#!/usr/bin/python3

import os
import requests
import subprocess
import shutil
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

def download_zip_and_upload_repos(org_name, output_dir="/tmp/repos", bucket_name=None):
    # Initialize S3 client
    s3_client = boto3.client("s3")
    
    # GH API URL to list organization repositories
    api_url = f"https://api.github.com/orgs/{org_name}/repos"
    headers = {"Accept": "application/vnd.github.v3+json"}
    
    repos = []
    page = 1
    
    print(f"Fetching repositories from the organization: {org_name}")
    
    while True:
        # Fetch repositories page by page
        response = requests.get(api_url, headers=headers, params={"page": page, "per_page": 100})
        if response.status_code != 200:
            print(f"Failed to fetch repositories: {response.status_code} {response.reason}")
            return
        
        data = response.json()
        if not data:
            break
        
        repos.extend(data)
        page += 1
    
    if not repos:
        print(f"No repositories found for the organization: {org_name}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Clone, zip, and upload each repository
    for repo in repos:
        repo_name = repo["name"]
        clone_url = repo["clone_url"]
        print(f"Cloning repository: {repo_name}")
        
        repo_dir = os.path.join(output_dir, repo_name)
        zip_file = os.path.join(output_dir, f"{repo_name}.zip")
        
        if os.path.exists(zip_file):
            print(f"Repository {repo_name} is already zipped. Skipping download and zip...")
            continue
        
        try:
            # Clone the repository
            subprocess.run(["git", "clone", clone_url, repo_dir], check=True)
            print(f"Repository {repo_name} cloned successfully.")
            
            # Zip the repository
            shutil.make_archive(zip_file.replace('.zip', ''), 'zip', repo_dir)
            print(f"Repository {repo_name} has been zipped to {zip_file}.")
            
            # Delete the cloned directory
            shutil.rmtree(repo_dir)
            print(f"Deleted the cloned directory for {repo_name}.")
            
            # Upload to S3
            print(f"Uploading {zip_file} to S3 bucket {bucket_name}...")    
            try:
                s3_client.upload_file(zip_file, bucket_name, os.path.basename(zip_file))
                print(f"Successfully uploaded {repo_name}.zip to S3.")
            except (NoCredentialsError, PartialCredentialsError) as e:
                print(f"Failed to upload {repo_name}.zip to S3: {e}")
            except Exception as e:
                print(f"An error occurred while processing {repo_name}: {e}")

    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository {repo_name}: {e}")
    except Exception as e:
        print(f"An error occurred while processing {repo_name}: {e}")
    
    print("All repositories have been downloaded, zipped, and uploaded to S3.")

# Usage
if __name__ == "__main__":
    org_name = "privacy-scaling-explorations"
    output_dir = "/tmp/repos"
    bucket_name = "pse-gh-repos-backup"
    download_zip_and_upload_repos(org_name, output_dir, bucket_name if bucket_name else None)
