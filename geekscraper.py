import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
import argparse
import concurrent.futures
import time
import sys
import re
from datetime import datetime, UTC
import json
import csv
import os
from typing import List, Dict, Union

def parse_page(url: str, page_num: int, verbose: bool = False) -> List[Dict[str, str]]:
    if verbose:
        print(f"[Page {page_num}] Fetching: {url}")

    try:
        start_time = time.time()
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        page_results = []

        for result in soup.select('div.list-col'):
            try:

                result_link = result.select_one('div.col-12.col-lg-4 a')
                result_url = f"https://browser.geekbench.com{result_link['href']}" if result_link else None

                system = result_link.text.strip() if result_link else "Unknown"
                model = ' '.join(result.select_one('span.list-col-model').stripped_strings)

                scores = result.select('span.list-col-text-score')
                single_core = scores[0].text.strip() if len(scores) > 0 else "N/A"
                multi_core = scores[1].text.strip() if len(scores) > 1 else "N/A"

                page_results.append({
                    'system': system,
                    'model': model,
                    'single_core': single_core,
                    'multi_core': multi_core,
                    'url': result_url
                })
            except Exception as e:
                if verbose:
                    print(f"  [Error] Parsing result: {str(e)}")

        elapsed = time.time() - start_time
        if verbose:
            print(f"[Page {page_num}] Found {len(page_results)} results in {elapsed:.2f}s")

        return page_results
    except Exception as e:
        if verbose:
            print(f"[Page {page_num}] Error: {str(e)}")
        return []

def parse_geekbench(query: str, max_pages: int = None, threads: int = 1, verbose: bool = False) -> List[Dict[str, str]]:
    base_url = "https://browser.geekbench.com"
    search_url = f"{base_url}/search?q={quote_plus(query)}"
    all_benchmarks = []

    if verbose:
        print(f"Starting search for: '{query}'")
        print(f"Threads: {threads}, Max pages: {max_pages or 'All'}")

    try:

        first_page = requests.get(search_url)
        first_page.raise_for_status()
        soup = BeautifulSoup(first_page.text, 'html.parser')

        pagination = soup.select_one('ul.pagination')
        total_pages = 1
        if pagination:
            page_links = [a for a in pagination.select('a.page-link') 
                         if a.text.strip().isdigit()]
            if page_links:
                total_pages = max(int(a.text) for a in page_links)

        pages_to_fetch = min(total_pages, max_pages) if max_pages else total_pages

        if verbose:
            print(f"Total pages available: {total_pages}")
            print(f"Pages to fetch: {pages_to_fetch}")

        urls = [search_url]  
        for page in range(2, pages_to_fetch + 1):
            urls.append(f"{search_url}&page={page}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []
            for i, url in enumerate(urls, 1):
                futures.append(executor.submit(parse_page, url, i, verbose))

            for future in concurrent.futures.as_completed(futures):
                all_benchmarks.extend(future.result())

        if verbose:
            print(f"\nTotal results collected: {len(all_benchmarks)}")

        return all_benchmarks
    except Exception as e:
        if verbose:
            print(f"Critical error: {str(e)}")
        return []

def calculate_statistics(benchmarks: List[Dict[str, str]]) -> Dict[str, float]:
    """Calculate statistics from benchmark results"""
    valid_scores = [
        (int(b['single_core']), int(b['multi_core']))
        for b in benchmarks
        if b['single_core'].isdigit() and b['multi_core'].isdigit()
    ]

    if not valid_scores:
        return {}

    single_scores = [s[0] for s in valid_scores]
    multi_scores = [s[1] for s in valid_scores]

    return {
        "mean_single_core": round(sum(single_scores) / len(single_scores), 2),
        "mean_multi_core": round(sum(multi_scores) / len(multi_scores), 2),
        "min_single_core": min(single_scores),
        "max_single_core": max(single_scores),
        "min_multi_core": min(multi_scores),
        "max_multi_core": max(multi_scores),
        "sample_count": len(valid_scores)
    }

def create_xml_output(benchmarks: List[Dict[str, str]], output_file: str) -> None:
    """Create XML output file"""
    root = ET.Element('benchmarks')
    for bench in benchmarks:
        benchmark_elem = ET.SubElement(root, 'benchmark')
        ET.SubElement(benchmark_elem, 'system').text = bench['system']
        ET.SubElement(benchmark_elem, 'model').text = bench['model']
        ET.SubElement(benchmark_elem, 'single_core_score').text = bench['single_core']
        ET.SubElement(benchmark_elem, 'multi_core_score').text = bench['multi_core']
        if 'url' in bench:
            ET.SubElement(benchmark_elem, 'url').text = bench['url']

    xml_str = ET.tostring(root, encoding='utf-8', method='xml').decode()
    with open(output_file, 'w') as f:
        f.write(xml_str)
    print(f"XML output saved to {output_file}")

def create_json_output(benchmarks: List[Dict[str, str]], output_file: str) -> None:
    """Create JSON output file with detailed results"""
    with open(output_file, 'w') as f:
        json.dump(benchmarks, f, indent=4)
    print(f"JSON output saved to {output_file}")

def create_stats_output(benchmarks: List[Dict[str, str]], output_file: str) -> None:
    """Create JSON file with statistics only"""
    stats = calculate_statistics(benchmarks)
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=4)
    print(f"Statistics JSON saved to {output_file}")

def create_csv_output(benchmarks: List[Dict[str, str]], output_file: str) -> None:
    """Create CSV output file"""
    fieldnames = ["system", "model", "single_core", "multi_core"]
    if benchmarks and 'url' in benchmarks[0]:
        fieldnames.append("url")

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(benchmarks)
    print(f"CSV output saved to {output_file}")

def safe_filename_component(s: str) -> str:
    """Sanitize string for use in filenames"""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', s)

def parse_input_file(file_path: str) -> Union[List[Dict[str, str]], None]:
    """Parse an input file containing benchmark results"""
    if not os.path.exists(file_path):
        print(f"Error: File not found - {file_path}", file=sys.stderr)
        return None

    try:
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                return json.load(f)
            elif file_path.endswith('.xml'):
                tree = ET.parse(file_path)
                root = tree.getroot()
                return [
                    {
                        'system': item.find('system').text if item.find('system') is not None else "Unknown",
                        'model': item.find('model').text if item.find('model') is not None else "Unknown",
                        'single_core': item.find('single_core_score').text if item.find('single_core_score') is not None else "N/A",
                        'multi_core': item.find('multi_core_score').text if item.find('multi_core_score') is not None else "N/A",
                        'url': item.find('url').text if item.find('url') is not None else None
                    }
                    for item in root.findall('benchmark')
                ]
            elif file_path.endswith('.csv'):
                with open(file_path, 'r') as f:
                    reader = csv.DictReader(f)
                    return list(reader)
            else:
                print(f"Unsupported file format - {file_path}", file=sys.stderr)
                return None
    except Exception as e:
        print(f"Error parsing file {file_path}: {str(e)}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Geekbench Parser - Scrape and analyze CPU benchmark results')
    parser.add_argument('query', nargs='?', help='Device model to search for (e.g., "sm-a566b")')
    parser.add_argument('-t', '--threads', type=int, default=1, help='Number of threads (default: 1)')
    parser.add_argument('-p', '--pages', type=int, help='Maximum number of pages (default: all)')
    parser.add_argument('-f', '--file', help='Parse results from file instead of web scraping')
    parser.add_argument('-o', '--output', help='Base name for output files (without extension)')
    parser.add_argument('--json', action='store_true', help='Output detailed results as JSON')
    parser.add_argument('--stats', action='store_true', help='Output statistics as JSON')
    parser.add_argument('--csv', action='store_true', help='Output results as CSV')
    parser.add_argument('--xml', action='store_true', help='Output results as XML')
    parser.add_argument('--all', action='store_true', help='Output all formats')

    args = parser.parse_args()

    if not args.query and not args.file:
        parser.error("Either a query or input file must be specified")

    if args.threads < 1:
        print("Thread count must be at least 1. Using 1 thread.")
        args.threads = 1

    verbose = True
    results = []

    if args.file:
        print(f"Parsing results from file: {args.file}")
        results = parse_input_file(args.file)
        if results is None:
            sys.exit(1)
    else:
        print(f"Searching for: '{args.query}' with {args.threads} thread(s)")
        start_time = time.time()
        results = parse_geekbench(args.query, max_pages=args.pages, threads=args.threads, verbose=verbose)
        elapsed = time.time() - start_time
        print(f"Scraping completed in {elapsed:.2f} seconds")

    if not results:
        print("No results found!", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
    if args.file:
        base_name = args.output or f"results_{timestamp}_parsed"
    else:
        sanitized_query = safe_filename_component(args.query)
        base_name = args.output or f"results_{timestamp}_{sanitized_query}"

    output_xml = args.xml or args.all
    output_json = args.json or args.all
    output_csv = args.csv or args.all
    output_stats = args.stats or args.all

    if not any([output_xml, output_json, output_csv, output_stats]):
        output_xml = True

    if output_xml:
        create_xml_output(results, f"{base_name}.xml")
    if output_json:
        create_json_output(results, f"{base_name}.json")
    if output_csv:
        create_csv_output(results, f"{base_name}.csv")
    if output_stats:
        stats_file = f"{base_name}_stats.json"
        create_stats_output(results, stats_file)

        stats = calculate_statistics(results)
        print("\nBenchmark Statistics:")
        print(json.dumps(stats, indent=4))

if __name__ == "__main__":
    main()