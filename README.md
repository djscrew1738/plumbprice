# ReconDesk

A powerful and user-friendly reconnaissance and information gathering CLI tool with interactive prompts.

## Features

ReconDesk provides an interactive command-line interface with comprehensive prompts for various reconnaissance tasks:

### Scan Types

- **Network Scan**: Comprehensive network reconnaissance with configurable options
  - Ping scan
  - Service detection
  - OS detection
  - Adjustable scan speed (Stealth, Normal, Fast, Aggressive)

- **Port Scan**: Flexible port scanning with multiple range options
  - Common ports (Top 100)
  - Well-known ports (1-1024)
  - All ports (1-65535)
  - Custom port ranges

- **DNS Enumeration**: Complete DNS information gathering
  - Multiple record types (A, AAAA, MX, NS, TXT, CNAME, SOA)
  - Reverse DNS lookup
  - Zone transfer attempts

- **Subdomain Discovery**: Advanced subdomain enumeration
  - Multiple discovery methods (Brute Force, Certificate Transparency, Search Engine)
  - Configurable wordlist sizes
  - Custom wordlist support

- **Web Application Scan**: Comprehensive web app analysis
  - Directory/file discovery
  - Technology detection
  - Security headers analysis
  - SSL/TLS analysis
  - Cookie analysis
  - Form detection
  - Custom User-Agent support

- **WHOIS Lookup**: Domain registration information

### Interactive Prompts

ReconDesk features a fully interactive CLI with:

- ✨ Beautiful themed prompts using the GreenPassion theme
- 🎯 Context-aware questions based on scan type
- ✅ Input validation and confirmation dialogs
- 📊 Real-time scan configuration preview
- 💾 Flexible output options (JSON, XML, HTML, TXT, CSV)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/recondesk.git
cd recondesk

# Install dependencies
pip install -r requirements.txt

# Or install with setup.py
python setup.py install
```

### Install in development mode

```bash
pip install -e .
```

## Usage

### Interactive Mode

Simply run the tool to enter interactive mode with prompts:

```bash
python recondesk.py
```

Or if installed:

```bash
recondesk
```

### Interactive Workflow

1. **Select Scan Type**: Choose from available reconnaissance methods
2. **Enter Target**: Provide the target IP, domain, or URL
3. **Configure Options**: Answer scan-specific prompts
4. **Set Output Options**: Choose output format and filename
5. **Confirm & Execute**: Review configuration and start scan
6. **View Results**: See results in terminal and/or saved file

## CLI Prompts Guide

### Main Menu Prompt

When you start ReconDesk, you'll see:

```
Select reconnaissance type:
> Network Scan
  Web Application Scan
  DNS Enumeration
  Subdomain Discovery
  Port Scan
  WHOIS Lookup
  Exit
```

Use arrow keys to navigate and Enter to select.

### Target Prompt

```
Enter target (IP address, domain, or URL): example.com
```

### Network Scan Prompts

```
Perform ping scan? (Y/n): Y
Enable service detection? (Y/n): Y
Enable OS detection? (Y/n): n
Select scan speed:
> Slow (Stealth)
  Normal
  Fast
  Aggressive
```

### Port Scan Prompts

```
Select port range:
> Common Ports (Top 100)
  Well-Known Ports (1-1024)
  All Ports (1-65535)
  Custom Range

[If Custom Range selected]
Enter port range (e.g., 1-1000 or 80,443,8080): 1-1000
```

### DNS Enumeration Prompts

```
Select DNS record types to query:
❯ ◉ A Records
  ◉ AAAA Records
  ◉ MX Records
  ◉ NS Records
  ◯ TXT Records
  ◯ CNAME Records
  ◯ SOA Records

Perform reverse DNS lookup? (Y/n): n
Attempt zone transfer? (Y/n): n
```

### Subdomain Discovery Prompts

```
Select discovery method:
> Brute Force
  Certificate Transparency
  Search Engine
  All Methods

Select wordlist size:
  Small (1000 entries)
> Medium (10000 entries)
  Large (100000 entries)
  Custom wordlist
```

### Web Application Scan Prompts

```
Select scan modules:
❯ ◉ Directory/File Discovery
  ◉ Technology Detection
  ◉ Security Headers
  ◯ SSL/TLS Analysis
  ◯ Cookie Analysis
  ◯ Form Detection

Follow redirects? (Y/n): Y
Check robots.txt? (Y/n): Y

Select User-Agent:
> Default
  Chrome
  Firefox
  Custom
```

### Output Options Prompts

```
Save results to file? (Y/n): Y

Select output format:
> JSON
  XML
  HTML Report
  Plain Text
  CSV

Enter output filename: recondesk_results
```

### Confirmation Prompt

Before executing, you'll see:

```
==================================================
SCAN CONFIGURATION
==================================================
  scan_type: network
  target: example.com
  ping_scan: True
  service_detection: True
  os_detection: False
  scan_speed: normal
  save_output: True
  output_format: json
  output_file: recondesk_results
==================================================

Proceed with this configuration? (Y/n): Y
```

## Examples

### Example 1: Network Scan

```bash
$ python recondesk.py

Select reconnaissance type: Network Scan
Enter target: 192.168.1.1
Perform ping scan? Y
Enable service detection? Y
Enable OS detection? n
Select scan speed: Normal
Save results to file? Y
Select output format: JSON
Enter output filename: network_scan_results
Proceed with this configuration? Y
```

### Example 2: Web Application Scan

```bash
$ python recondesk.py

Select reconnaissance type: Web Application Scan
Enter target: https://example.com
Select scan modules: [Directory/File Discovery, Technology Detection, Security Headers]
Follow redirects? Y
Check robots.txt? Y
Select User-Agent: Chrome
Save results to file? Y
Select output format: HTML Report
Enter output filename: webapp_report
Proceed with this configuration? Y
```

### Example 3: DNS Enumeration

```bash
$ python recondesk.py

Select reconnaissance type: DNS Enumeration
Enter target: example.com
Select DNS record types: [A Records, MX Records, NS Records, TXT Records]
Perform reverse DNS lookup? Y
Attempt zone transfer? n
Save results to file? Y
Select output format: JSON
Enter output filename: dns_results
Proceed with this configuration? Y
```

## Output Formats

ReconDesk supports multiple output formats:

- **JSON**: Structured data format, ideal for parsing
- **XML**: XML format for integration with other tools
- **HTML**: Beautiful HTML reports for easy viewing
- **TXT**: Plain text format for simple reading
- **CSV**: Comma-separated values for spreadsheet analysis

## Development

### Project Structure

```
recondesk/
├── LICENSE                 # GPL-3.0 License
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── setup.py              # Package setup file
├── .gitignore            # Git ignore rules
├── recondesk.py          # Main entry point
└── recondesk/
    ├── __init__.py       # Package initialization
    ├── cli.py            # CLI interface with prompts
    └── scanner.py        # Scanner implementation
```

### Adding New Scan Types

To add a new scan type:

1. Add the scan type to the main menu in `cli.py`
2. Create a prompt function for scan-specific options
3. Implement the scan logic in `scanner.py`

### Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See the [LICENSE](LICENSE) file for details.

## Disclaimer

ReconDesk is designed for authorized security testing, educational purposes, and defensive security research. Users are responsible for ensuring they have proper authorization before scanning any targets. Unauthorized access to computer systems is illegal.

## Author

ReconDesk Team

## Support

For issues, questions, or contributions, please visit the project repository.
