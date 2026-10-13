import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.generate as module

import yaml

from scripts.generate import Resolver, generate, normalize, parse_clash, parse_meta, parse_v2fly
from scripts.ip_rules import IPResult, _google_prefixes, _request, normalized_network, resolve_ip_source, sorted_networks, subtract_networks
from scripts.render_catalog import render
from scripts.validate import validate


class GeneratorTests(unittest.TestCase):
    def test_normalization_and_malformed_input(self):
        self.assertEqual(normalize('ExAmPlE.COM.'), 'example.com')
        for item in ('*.example.com', 'https://example.com', 'example.com/path', '', 'localhost'):
            self.assertIsNone(normalize(item))
        for item in ('1e100.net', 'foo.2example.com', '466453.com'):
            self.assertIsNone(normalize(item))
        self.assertEqual(normalize('accounts.google.com'), 'accounts.google.com')

    def test_cidr_validation_and_collapse(self):
        self.assertEqual(str(normalized_network('8.8.8.1/24')), '8.8.8.0/24')
        self.assertEqual(str(normalized_network('2001:4860:4860::8888/32')), '2001:4860::/32')
        for item in ('8.8.8.8', '8.8.8.0/33', '192.168.0.0/16', '2001:db8::/32'):
            with self.assertRaises(ValueError):
                normalized_network(item)
        ranges = [normalized_network(value) for value in ('8.8.8.0/25', '8.8.8.128/25', '8.8.8.0/24', '2606:4700::/33', '2606:4700:8000::/33')]
        self.assertEqual(tuple(map(str, sorted_networks(ranges))), ('8.8.8.0/24', '2606:4700::/32'))

    def test_google_cloud_subtraction(self):
        owned = _google_prefixes({'prefixes': [{'ipv4Prefix': '8.8.0.0/16'}, {'ipv6Prefix': '2001:4860::/32'}]})
        cloud = _google_prefixes({'prefixes': [{'ipv4Prefix': '8.8.8.0/24'}, {'ipv6Prefix': '2001:4860:8000::/33'}]})
        result = subtract_networks(owned, cloud)
        self.assertTrue(result)
        self.assertTrue(all(not item.overlaps(excluded) for item in result for excluded in cloud))
        self.assertLess(sum(item.num_addresses for item in result), sum(item.num_addresses for item in owned))

    def test_google_source_provenance(self):
        source = {'format': 'google-services', 'url': 'https://example.com/goog.json',
                  'exclude_url': 'https://example.com/cloud.json'}
        owned = {'creationTime': '2026-10-12T00:00:00Z', 'prefixes': [{'ipv4Prefix': '8.8.0.0/16'}]}
        cloud = {'creationTime': '2026-10-11T00:00:00Z', 'prefixes': [{'ipv4Prefix': '8.8.8.0/24'}]}
        with patch('scripts.ip_rules._json', side_effect=[(owned, {}), (cloud, {})]):
            result = resolve_ip_source(source, '2026-10-12T01:00:00Z')
        self.assertIn(source['url'], result.source_updated_at)
        self.assertEqual(result.retrieved_at, '2026-10-12T01:00:00Z')
        self.assertTrue(all(not item.overlaps(normalized_network('8.8.8.0/24')) for item in result.networks))

    def test_github_api_requests_use_token_only_for_github_api(self):
        with patch.dict('os.environ', {'GH_TOKEN': 'test-token'}), patch('scripts.ip_rules.urllib.request.urlopen') as urlopen:
            response = urlopen.return_value.__enter__.return_value
            response.status = 200
            response.headers = {}
            response.read.return_value = b'[]'
            _request('https://api.github.com/repos/example/project/commits')
            api_request = urlopen.call_args.args[0]
            self.assertEqual(api_request.get_header('Authorization'), 'Bearer test-token')

            _request('https://raw.githubusercontent.com/example/project/main/data.txt')
            raw_request = urlopen.call_args.args[0]
            self.assertIsNone(raw_request.get_header('Authorization'))

    def test_v2fly_recursive_include_and_cycle(self):
        sources = {'parent': {'include': ['child']}, 'child': {'domains': ['Example.COM']}}
        self.assertEqual(Resolver(sources).resolve('parent'), {'example.com'})
        sources['child']['include'] = ['parent']
        with self.assertRaisesRegex(ValueError, 'circular'):
            Resolver(sources).resolve('parent')

    def test_parsers_report_unsupported(self):
        domains, unsupported, includes = parse_v2fly('include:child\nfull:Mail.Example.com\n1e100.net\nregexp:bad.*\n')
        self.assertEqual(domains, {'mail.example.com'})
        self.assertEqual(includes, ['child'])
        self.assertEqual(len(unsupported), 2)
        domains, unsupported = parse_clash('DOMAIN-SUFFIX,Example.com\nDOMAIN-KEYWORD,example\nIP-CIDR,192.0.2.0/24\n')
        self.assertEqual(domains, {'example.com'})
        self.assertEqual(len(unsupported), 2)

    def test_meta_payload(self):
        domains, unsupported = parse_meta('payload:\n  - +.example.com\n  - bad/path\n')
        self.assertEqual(domains, {'example.com'})
        self.assertEqual(len(unsupported), 1)

    def test_google_aggregation_and_provider_independence(self):
        config = {'providers': {
            'google': {
                'core': {'output': 'output/google/google-core-domains.txt', 'sources': ['core']},
                'other': {'output': 'output/google/google-other-domains.txt', 'sources': ['broad'], 'remaining': True},
                'all': {'output': 'output/google/google-all-domains.txt', 'sources': []},
            },
            'apple': {'all': {'output': 'output/apple/apple-all-domains.txt', 'sources': ['apple']}},
        }}
        resolver = Resolver({'core': {'domains': ['google.com']},
                             'broad': {'domains': ['google.com', 'youtube.com']},
                             'apple': {'domains': ['apple.com']}})
        outputs, _ = generate(config, resolver)
        self.assertEqual(outputs['google-other'], {'youtube.com'})
        self.assertEqual(outputs['google-all'], outputs['google-core'] | outputs['google-other'])
        self.assertEqual(outputs['apple-all'], {'apple.com'})

    def test_fetch_failure_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / 'output/apple/apple-all-domains.txt'
            previous.parent.mkdir(parents=True)
            previous.write_text('apple.com\n')
            config = root / 'services.yml'
            config.write_text(yaml.safe_dump({
                'sources': {'remote': {'format': 'v2fly', 'url': 'https://example.com/rules'}},
                'providers': {'apple': {'all': {
                    'output': 'output/apple/apple-all-domains.txt', 'sources': ['remote']}}},
            }))
            with patch('sys.argv', ['generate', '--config', str(config), '--output-root', str(root)]), patch.object(module, 'fetch', side_effect=OSError('offline')):
                with self.assertRaisesRegex(OSError, 'offline'):
                    module.main()
            self.assertEqual(previous.read_text(), 'apple.com\n')

    def test_generation_and_validation_use_separate_output_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_root = root / 'published-lists'
            config = root / 'services.yml'
            config.write_text(yaml.safe_dump({
                'sources': {'curated': {'domains': ['example.com']}},
                'providers': {'google': {
                    'core': {'output': 'output/google/google-core-domains.txt', 'sources': ['curated']},
                    'all': {'output': 'output/google/google-all-domains.txt', 'sources': []},
                }},
            }))
            with patch('sys.argv', ['generate', '--config', str(config), '--output-root', str(output_root)]):
                module.main()
            validate(output_root)
            self.assertEqual(
                (output_root / 'output/google/google-all-domains.txt').read_text(),
                'example.com\n',
            )
            self.assertFalse((root / 'output').exists())

    def test_canonical_names_replace_old_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'output/google'
            output.mkdir(parents=True)
            for name in ('google-all.txt', 'google-all-all-v4.txt'):
                (output / name).write_text('obsolete\n')
            config = root / 'services.yml'
            config.write_text(yaml.safe_dump({
                'sources': {'curated': {'domains': ['example.com']}},
                'providers': {'google': {
                    'core': {'output': 'output/google/google-core-domains.txt', 'sources': ['curated']},
                    'all': {'output': 'output/google/google-all-domains.txt', 'sources': []},
                }},
                'ip_sources': {'owned': {}},
                'ip_lists': {'google-all': 'owned'},
            }))
            source = 'https://example.com/owned'
            result = IPResult((normalized_network('8.8.8.0/24'),
                               normalized_network('2001:4860::/32')),
                              (source,), {source: '2026-10-12T00:00:00Z'},
                              '2026-10-12T01:00:00Z')
            with patch('sys.argv', ['generate', '--config', str(config), '--output-root', str(root)]), \
                 patch.object(module, 'resolve_ip_source', return_value=result):
                module.main()
            validate(root)
            self.assertEqual({path.name for path in output.glob('*.txt')}, {
                'google-core-domains.txt', 'google-all-domains.txt',
                'google-all-ips-v4.txt', 'google-all-ips-v6.txt',
                'google-all-ips.txt', 'google-all-combined-v4.txt',
                'google-all-combined-v6.txt', 'google-all-combined.txt',
            })
            self.assertIn('google-all-combined-v4.txt', render(root))
            self.assertEqual((output / 'google-all-combined-v4.txt').read_text(),
                             'example.com\n8.8.8.0/24\n')

    def test_empty_list_rejected(self):
        config = {'providers': {'apple': {'all': {'output': 'output/apple/apple-all-domains.txt', 'sources': ['empty']}}}}
        with self.assertRaisesRegex(ValueError, 'empty output'):
            generate(config, Resolver({'empty': {'domains': []}}))


if __name__ == '__main__':
    unittest.main()
