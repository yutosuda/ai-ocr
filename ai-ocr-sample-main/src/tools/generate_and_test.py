#!/usr/bin/env python
"""
Generate sample Excel files and process them through the AI-OCR system.
This is a utility script to help users test the system with sample data.
"""
import argparse
import json
import os
import requests
import sys
import time
from pathlib import Path

# Add parent directory to path so we can import from processor
sys.path.append(str(Path(__file__).parent.parent))
from processor.create_test_data import generate_invoice, generate_sales_report, generate_product_catalog


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate and test AI-OCR system")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000",
                        help="URL of the API service")
    parser.add_argument("--output-dir", type=str, default="test_samples",
                        help="Directory to store generated test files")
    parser.add_argument("--num-files", type=int, default=1,
                        help="Number of each type of file to generate")
    parser.add_argument("--extract", action="store_true",
                        help="Process the generated files through the AI-OCR system")
    parser.add_argument("--wait-time", type=int, default=5,
                        help="Wait time in seconds between polling for job status")
    return parser.parse_args()


def create_output_dir(output_dir):
    """Create output directory if it doesn't exist."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    return output_path


def generate_test_files(output_dir, num_files):
    """Generate test files of different types."""
    files_info = []
    
    # Generate invoices
    for i in range(1, num_files + 1):
        invoice_path = output_dir / f"invoice_{i}.xlsx"
        invoice_number, total_amount = generate_invoice(invoice_path, i)
        files_info.append({
            "path": str(invoice_path),
            "type": "invoice",
            "info": {
                "invoice_number": invoice_number,
                "total_amount": total_amount
            }
        })
        print(f"Generated invoice: {invoice_path} - Invoice #{invoice_number}, Total: ${total_amount:.2f}")
    
    # Generate sales reports
    for i in range(1, num_files + 1):
        report_path = output_dir / f"sales_report_{i}.xlsx"
        report_month, total_sales = generate_sales_report(report_path, i)
        files_info.append({
            "path": str(report_path),
            "type": "report",
            "info": {
                "period": report_month,
                "total_sales": total_sales
            }
        })
        print(f"Generated sales report: {report_path} - Period: {report_month}, Total Sales: ${total_sales:.2f}")
    
    # Generate product catalogs
    for i in range(1, num_files + 1):
        catalog_path = output_dir / f"product_catalog_{i}.xlsx"
        num_products, num_categories = generate_product_catalog(catalog_path, i)
        files_info.append({
            "path": str(catalog_path),
            "type": "catalog",
            "info": {
                "products": num_products,
                "categories": num_categories
            }
        })
        print(f"Generated product catalog: {catalog_path} - Products: {num_products}, Categories: {num_categories}")
    
    return files_info


def upload_document(api_url, file_path):
    """Upload a document to the API service."""
    url = f"{api_url}/api/v1/documents"
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        response = requests.post(url, files=files)
    
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error uploading {file_path}: {response.text}")
        return None


def create_job(api_url, document_id):
    """Create a processing job for a document."""
    url = f"{api_url}/api/v1/jobs"
    data = {"document_id": document_id}
    response = requests.post(url, json=data)
    
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error creating job for document {document_id}: {response.text}")
        return None


def get_job_status(api_url, job_id):
    """Get the status of a processing job."""
    url = f"{api_url}/api/v1/jobs/{job_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting job status for {job_id}: {response.text}")
        return None


def get_extraction_result(api_url, job_id):
    """Get the extraction result for a job."""
    url = f"{api_url}/api/v1/extractions/job/{job_id}"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error getting extraction result for job {job_id}: {response.text}")
        return None


def process_files(api_url, files_info, wait_time):
    """Process files through the AI-OCR system."""
    results = []
    
    for file_info in files_info:
        print(f"\nProcessing {file_info['path']}...")
        
        # Upload document
        print("Uploading document...")
        upload_result = upload_document(api_url, file_info["path"])
        if not upload_result:
            print("Upload failed, skipping to next file")
            continue
        
        document_id = upload_result["document_id"]
        print(f"Document uploaded with ID: {document_id}")
        
        # Create job
        print("Creating processing job...")
        job_result = create_job(api_url, document_id)
        if not job_result:
            print("Job creation failed, skipping to next file")
            continue
        
        job_id = job_result["job_id"]
        print(f"Job created with ID: {job_id}")
        
        # Poll for job completion
        print("Waiting for processing to complete...")
        job_complete = False
        start_time = time.time()
        while not job_complete:
            job_status = get_job_status(api_url, job_id)
            if not job_status:
                print("Could not get job status, skipping to next file")
                break
            
            status = job_status["status"]
            progress = job_status.get("progress", 0)
            print(f"Status: {status}, Progress: {progress:.1f}%")
            
            if status in ["completed", "failed", "canceled"]:
                job_complete = True
            else:
                print(f"Waiting {wait_time} seconds before checking again...")
                time.sleep(wait_time)
            
            # Timeout after 5 minutes
            if time.time() - start_time > 300:
                print("Timeout after 5 minutes, skipping to next file")
                break
        
        if not job_complete:
            continue
        
        # Get extraction result
        if job_status["status"] == "completed":
            print("Getting extraction result...")
            extraction_result = get_extraction_result(api_url, job_id)
            if extraction_result:
                print(f"Extraction completed with confidence: {extraction_result.get('confidence_score', 0):.2f}")
                
                # Add result to list
                results.append({
                    "file_path": file_info["path"],
                    "file_type": file_info["type"],
                    "expected_info": file_info["info"],
                    "document_id": document_id,
                    "job_id": job_id,
                    "confidence_score": extraction_result.get("confidence_score", 0),
                    "extracted_data": extraction_result.get("extracted_data", {})
                })
                
                # Save individual result to file
                result_path = Path(file_info["path"]).with_suffix(".json")
                with open(result_path, "w") as f:
                    json.dump(extraction_result.get("extracted_data", {}), f, indent=2)
                print(f"Extraction result saved to {result_path}")
            else:
                print("Could not get extraction result")
        else:
            print(f"Job failed with status: {job_status['status']}")
            if job_status.get("error"):
                print(f"Error: {job_status['error']}")
    
    return results


def save_results(results, output_dir):
    """Save processing results to a JSON file."""
    results_path = Path(output_dir) / "extraction_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAll results saved to {results_path}")


def main():
    """Main function."""
    args = parse_args()
    output_dir = create_output_dir(args.output_dir)
    
    print(f"Generating {args.num_files} files of each type in {output_dir}")
    files_info = generate_test_files(output_dir, args.num_files)
    
    if args.extract:
        print(f"\nProcessing files through AI-OCR system at {args.api_url}")
        results = process_files(args.api_url, files_info, args.wait_time)
        save_results(results, output_dir)
    else:
        print("\nSkipping extraction processing (use --extract to process files)")
    
    print("\nDone!")


if __name__ == "__main__":
    main() 