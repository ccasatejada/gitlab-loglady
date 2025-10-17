#!/usr/bin/env python3
"""Script to organize existing changelogs by year, grouped by date."""

import re
from collections import defaultdict
from pathlib import Path
from datetime import datetime
# only used to fetch
# Product mapping with their changelog locations
PRODUCTS = {
    # 'Product1': '/path/to/repository/CHANGELOG.md',
    # 'Product2': '/path/to/repository/CHANGELOG.md',
}

def extract_date_from_header(header_line):
    """Extract date information from changelog header line.

    Returns tuple: (year, datetime_obj, clean_header_without_product)
    """
    # Remove ## and product prefix if present
    header = header_line.replace('##', '').strip()

    # Match patterns like "25/09/2025, en prod le 02/10/2025" or "MEP 09/10/2025, en prod le 16/10/2025"
    match = re.search(r'(\d{2})/(\d{2})/(\d{4})', header)
    if match:
        day, month, year = match.groups()
        date_obj = datetime(int(year), int(month), int(day))

        # Extract the full date string from header (everything after potential "MEP" prefix)
        date_match = re.search(r'(MEP\s+)?(\d{2}/\d{2}/\d{4}.*)', header)
        if date_match:
            clean_header = date_match.group(2)
        else:
            clean_header = header

        return (int(year), date_obj, clean_header)
    return (None, None, None)

def parse_changelog(file_path, product_name):
    """Parse a changelog file and extract entries grouped by date."""
    entries_by_date = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Warning: {file_path} not found")
        return entries_by_date

    # Split by headers (lines starting with ##)
    lines = content.split('\n')
    current_changes = []
    current_date_info = None

    for line in lines:
        if line.startswith('## ') and not line.startswith('## #'):
            # Save previous entry
            if current_changes and current_date_info:
                year, date_obj, clean_header = current_date_info
                if year:
                    date_key = clean_header  # Use clean header as key
                    if date_key not in entries_by_date:
                        entries_by_date[date_key] = {
                            'year': year,
                            'date_obj': date_obj,
                            'products': {}
                        }
                    entries_by_date[date_key]['products'][product_name] = current_changes

            # Start new entry
            current_date_info = extract_date_from_header(line)
            current_changes = []
        elif current_date_info and current_date_info[0] is not None:
            # Collect change lines (skip empty lines at the start)
            stripped = line.strip()
            if stripped or current_changes:  # Start collecting after first non-empty line
                current_changes.append(line)

    # Save last entry
    if current_changes and current_date_info:
        year, date_obj, clean_header = current_date_info
        if year:
            date_key = clean_header
            if date_key not in entries_by_date:
                entries_by_date[date_key] = {
                    'year': year,
                    'date_obj': date_obj,
                    'products': {}
                }
            entries_by_date[date_key]['products'][product_name] = current_changes

    return entries_by_date

def merge_date_entries(all_dates_data):
    """Merge entries from different products by date."""
    merged = {}

    for product, dates_data in all_dates_data.items():
        for date_key, date_info in dates_data.items():
            if date_key not in merged:
                merged[date_key] = {
                    'year': date_info['year'],
                    'date_obj': date_info['date_obj'],
                    'products': {}
                }
            # Merge products for this date
            merged[date_key]['products'].update(date_info['products'])

    return merged

def main():
    """Main function to organize all changelogs."""
    all_dates_data = {}

    # Parse all changelog files
    for product, file_path in PRODUCTS.items():
        print(f"Processing {product}...")
        entries = parse_changelog(file_path, product)
        if entries:
            all_dates_data[product] = entries

    # Merge all entries by date
    merged_by_date = merge_date_entries(all_dates_data)

    # Group by year
    entries_by_year = defaultdict(list)
    for date_key, date_info in merged_by_date.items():
        entries_by_year[date_info['year']].append({
            'date_key': date_key,
            'date_obj': date_info['date_obj'],
            'products': date_info['products']
        })

    # Write organized files by year
    archive_dir = Path('/changelog_archive')
    archive_dir.mkdir(exist_ok=True)

    total_entries = 0
    for year in sorted(entries_by_year.keys(), reverse=True):
        output_file = archive_dir / f'{year}.md'

        # Sort entries by date (newest first)
        year_entries = sorted(
            entries_by_year[year],
            key=lambda x: x['date_obj'],
            reverse=True
        )

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f'# Changelog {year}\n\n')
            f.write('All product changelogs organized by release date.\n\n')

            for entry in year_entries:
                # Write date header
                f.write(f"## {entry['date_key']}\n")

                # Write changes grouped by product
                for product_name in sorted(entry['products'].keys()):
                    changes = entry['products'][product_name]
                    f.write(f"**{product_name}**\n")

                    # Write changes, cleaning up extra blank lines
                    for line in changes:
                        if line.strip() or not changes[0].strip():  # Preserve structure
                            f.write(line + '\n')

                    f.write('\n')  # Blank line between products

                total_entries += 1

        print(f"Created {output_file} with {len(year_entries)} date entries")

    print(f"\nTotal years processed: {len(entries_by_year)}")
    print(f"Total date entries: {total_entries}")
    print(f"Years: {sorted(entries_by_year.keys())}")

if __name__ == '__main__':
    main()
