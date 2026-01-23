#!/usr/bin/env python3
"""
CLI interface for ReconDesk with interactive prompts
"""

import sys
import argparse
from typing import Dict, Any

try:
    import inquirer
    from inquirer.themes import GreenPassion
except ImportError:
    print("Error: Required dependencies not installed.")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

from recondesk.scanner import ReconScanner


def display_banner():
    """Display the ReconDesk banner"""
    banner = """
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║           RECONDESK v1.0.0                   ║
    ║   Reconnaissance & Information Gathering     ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """
    print(banner)


def get_scan_type_prompt() -> str:
    """Prompt user to select scan type"""
    questions = [
        inquirer.List(
            'scan_type',
            message="Select reconnaissance type",
            choices=[
                ('Network Scan', 'network'),
                ('Web Application Scan', 'webapp'),
                ('DNS Enumeration', 'dns'),
                ('Subdomain Discovery', 'subdomain'),
                ('Port Scan', 'port'),
                ('WHOIS Lookup', 'whois'),
                ('Exit', 'exit')
            ],
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())
    return answers['scan_type'] if answers else 'exit'


def get_target_prompt() -> str:
    """Prompt user for target"""
    questions = [
        inquirer.Text(
            'target',
            message="Enter target (IP address, domain, or URL)",
            validate=lambda _, x: len(x) > 0,
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())
    return answers['target'] if answers else ''


def get_network_scan_options() -> Dict[str, Any]:
    """Prompt for network scan specific options"""
    questions = [
        inquirer.Confirm(
            'ping_scan',
            message="Perform ping scan?",
            default=True,
        ),
        inquirer.Confirm(
            'service_detection',
            message="Enable service detection?",
            default=True,
        ),
        inquirer.Confirm(
            'os_detection',
            message="Enable OS detection?",
            default=False,
        ),
        inquirer.List(
            'scan_speed',
            message="Select scan speed",
            choices=[
                ('Slow (Stealth)', 'slow'),
                ('Normal', 'normal'),
                ('Fast', 'fast'),
                ('Aggressive', 'aggressive'),
            ],
            default='normal',
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())
    return answers if answers else {}


def get_port_scan_options() -> Dict[str, Any]:
    """Prompt for port scan specific options"""
    questions = [
        inquirer.List(
            'port_range',
            message="Select port range",
            choices=[
                ('Common Ports (Top 100)', 'common'),
                ('Well-Known Ports (1-1024)', 'wellknown'),
                ('All Ports (1-65535)', 'all'),
                ('Custom Range', 'custom'),
            ],
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())

    if answers and answers['port_range'] == 'custom':
        custom_question = [
            inquirer.Text(
                'custom_ports',
                message="Enter port range (e.g., 1-1000 or 80,443,8080)",
            ),
        ]
        custom_answer = inquirer.prompt(custom_question, theme=GreenPassion())
        answers.update(custom_answer if custom_answer else {})

    return answers if answers else {}


def get_dns_enumeration_options() -> Dict[str, Any]:
    """Prompt for DNS enumeration options"""
    questions = [
        inquirer.Checkbox(
            'record_types',
            message="Select DNS record types to query",
            choices=[
                ('A Records', 'A'),
                ('AAAA Records', 'AAAA'),
                ('MX Records', 'MX'),
                ('NS Records', 'NS'),
                ('TXT Records', 'TXT'),
                ('CNAME Records', 'CNAME'),
                ('SOA Records', 'SOA'),
            ],
            default=['A', 'MX', 'NS'],
        ),
        inquirer.Confirm(
            'reverse_lookup',
            message="Perform reverse DNS lookup?",
            default=False,
        ),
        inquirer.Confirm(
            'zone_transfer',
            message="Attempt zone transfer?",
            default=False,
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())
    return answers if answers else {}


def get_subdomain_discovery_options() -> Dict[str, Any]:
    """Prompt for subdomain discovery options"""
    questions = [
        inquirer.List(
            'method',
            message="Select discovery method",
            choices=[
                ('Brute Force', 'bruteforce'),
                ('Certificate Transparency', 'cert'),
                ('Search Engine', 'search'),
                ('All Methods', 'all'),
            ],
            default='all',
        ),
        inquirer.List(
            'wordlist',
            message="Select wordlist size",
            choices=[
                ('Small (1000 entries)', 'small'),
                ('Medium (10000 entries)', 'medium'),
                ('Large (100000 entries)', 'large'),
                ('Custom wordlist', 'custom'),
            ],
            default='medium',
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())

    if answers and answers['wordlist'] == 'custom':
        custom_question = [
            inquirer.Text(
                'wordlist_path',
                message="Enter path to custom wordlist",
            ),
        ]
        custom_answer = inquirer.prompt(custom_question, theme=GreenPassion())
        answers.update(custom_answer if custom_answer else {})

    return answers if answers else {}


def get_webapp_scan_options() -> Dict[str, Any]:
    """Prompt for web application scan options"""
    questions = [
        inquirer.Checkbox(
            'scan_modules',
            message="Select scan modules",
            choices=[
                ('Directory/File Discovery', 'directory'),
                ('Technology Detection', 'tech'),
                ('Security Headers', 'headers'),
                ('SSL/TLS Analysis', 'ssl'),
                ('Cookie Analysis', 'cookies'),
                ('Form Detection', 'forms'),
            ],
            default=['directory', 'tech', 'headers'],
        ),
        inquirer.Confirm(
            'follow_redirects',
            message="Follow redirects?",
            default=True,
        ),
        inquirer.Confirm(
            'check_robots',
            message="Check robots.txt?",
            default=True,
        ),
        inquirer.List(
            'user_agent',
            message="Select User-Agent",
            choices=[
                ('Default', 'default'),
                ('Chrome', 'chrome'),
                ('Firefox', 'firefox'),
                ('Custom', 'custom'),
            ],
            default='default',
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())

    if answers and answers['user_agent'] == 'custom':
        custom_question = [
            inquirer.Text(
                'custom_user_agent',
                message="Enter custom User-Agent string",
            ),
        ]
        custom_answer = inquirer.prompt(custom_question, theme=GreenPassion())
        answers.update(custom_answer if custom_answer else {})

    return answers if answers else {}


def get_output_options() -> Dict[str, Any]:
    """Prompt for output options"""
    questions = [
        inquirer.Confirm(
            'save_output',
            message="Save results to file?",
            default=True,
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())

    if answers and answers.get('save_output'):
        output_questions = [
            inquirer.List(
                'output_format',
                message="Select output format",
                choices=[
                    ('JSON', 'json'),
                    ('XML', 'xml'),
                    ('HTML Report', 'html'),
                    ('Plain Text', 'txt'),
                    ('CSV', 'csv'),
                ],
                default='json',
            ),
            inquirer.Text(
                'output_file',
                message="Enter output filename",
                default='recondesk_results',
            ),
        ]
        output_answers = inquirer.prompt(output_questions, theme=GreenPassion())
        answers.update(output_answers if output_answers else {})

    return answers if answers else {}


def confirm_scan(scan_config: Dict[str, Any]) -> bool:
    """Display scan configuration and ask for confirmation"""
    print("\n" + "="*50)
    print("SCAN CONFIGURATION")
    print("="*50)
    for key, value in scan_config.items():
        print(f"  {key}: {value}")
    print("="*50 + "\n")

    questions = [
        inquirer.Confirm(
            'confirm',
            message="Proceed with this configuration?",
            default=True,
        ),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion())
    return answers['confirm'] if answers else False


def interactive_mode():
    """Run ReconDesk in interactive mode with prompts"""
    display_banner()

    print("Welcome to ReconDesk - Interactive Mode\n")

    while True:
        # Get scan type
        scan_type = get_scan_type_prompt()

        if scan_type == 'exit':
            print("\nThank you for using ReconDesk!")
            break

        # Get target
        target = get_target_prompt()
        if not target:
            print("No target specified. Returning to main menu.\n")
            continue

        # Build scan configuration
        scan_config = {
            'scan_type': scan_type,
            'target': target,
        }

        # Get scan-specific options
        if scan_type == 'network':
            options = get_network_scan_options()
            scan_config.update(options)
        elif scan_type == 'port':
            options = get_port_scan_options()
            scan_config.update(options)
        elif scan_type == 'dns':
            options = get_dns_enumeration_options()
            scan_config.update(options)
        elif scan_type == 'subdomain':
            options = get_subdomain_discovery_options()
            scan_config.update(options)
        elif scan_type == 'webapp':
            options = get_webapp_scan_options()
            scan_config.update(options)

        # Get output options
        output_options = get_output_options()
        scan_config.update(output_options)

        # Confirm and execute
        if confirm_scan(scan_config):
            scanner = ReconScanner(scan_config)
            print("\n[*] Starting scan...\n")
            results = scanner.execute()

            if results:
                print("\n[+] Scan completed successfully!")
                if scan_config.get('save_output'):
                    print(f"[+] Results saved to: {results.get('output_file', 'output file')}")
            else:
                print("\n[-] Scan failed or was interrupted.")
        else:
            print("\n[!] Scan cancelled.\n")

        # Ask if user wants to run another scan
        questions = [
            inquirer.Confirm(
                'continue',
                message="Run another scan?",
                default=True,
            ),
        ]
        answers = inquirer.prompt(questions, theme=GreenPassion())
        if not answers or not answers['continue']:
            print("\nThank you for using ReconDesk!")
            break
        print()


def main():
    """Main entry point for ReconDesk CLI"""
    parser = argparse.ArgumentParser(
        description='ReconDesk - Reconnaissance & Information Gathering Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  recondesk.py                    # Interactive mode with prompts
  recondesk.py -i                 # Interactive mode (explicit)

For more information, visit: https://github.com/yourusername/recondesk
        """
    )

    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Run in interactive mode (default)',
    )

    parser.add_argument(
        '--version',
        action='version',
        version='ReconDesk 1.0.0',
    )

    args = parser.parse_args()

    try:
        interactive_mode()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
