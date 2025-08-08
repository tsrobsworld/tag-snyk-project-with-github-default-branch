import requests
import json
import os
import sys
import time
import datetime
import logging
import argparse
from typing import Dict, List, Optional, Tuple


# Valid integration types for source_types parameter
VALID_INTEGRATION_TYPES = {
    'github',
    'github-enterprise', 
    'github-cloud-app'
}


def validate_integration_types(integration_types: List[str]) -> List[str]:
    """
    Validate integration types against allowed values.
    
    Args:
        integration_types: List of integration types to validate
        
    Returns:
        List of validated integration types
        
    Raises:
        ValueError: If any integration type is invalid
    """
    if not integration_types:
        return []
    
    invalid_types = [t for t in integration_types if t not in VALID_INTEGRATION_TYPES]
    if invalid_types:
        raise ValueError(f"Invalid integration types: {invalid_types}. Valid types are: {', '.join(VALID_INTEGRATION_TYPES)}")
    
    return integration_types


class ErrorLogger:
    """Class to handle error logging for projects that couldn't be tagged."""
    
    def __init__(self, log_file: str = "tagging_errors.log"):
        self.log_file = log_file
        self.errors = []
    
    def log_error(self, error_type: str, details: Dict, project_info: Dict = None):
        """
        Log an error with details.
        
        Args:
            error_type: Type of error (e.g., 'missing_owner', 'api_error', etc.)
            details: Error details
            project_info: Project information for context
        """
        error_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'error_type': error_type,
            'details': details,
            'project_info': project_info
        }
        self.errors.append(error_entry)
        print(f"   ⚠️  Error logged: {error_type}")
    
    def save_log(self):
        """Save all errors to the log file."""
        if self.errors:
            try:
                with open(self.log_file, 'w') as f:
                    json.dump(self.errors, f, indent=2)
                print(f"\n📝 Error log saved to: {self.log_file}")
                print(f"   Total errors logged: {len(self.errors)}")
            except Exception as e:
                print(f"❌ Failed to save error log: {e}")
        else:
            print("\n✅ No errors logged - all projects processed successfully!")
    
    def get_summary(self) -> Dict:
        """Get a summary of errors by type."""
        summary = {}
        for error in self.errors:
            error_type = error['error_type']
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary


class SnykAPI:
    """Snyk API client for collecting snyk target and project data ."""
    
    def __init__(self, token: str, region: str = "SNYK-US-01"):
        self.token = token
        self.base_url = self._get_base_url(region)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Content-Type': 'application/vnd.api+json',
            'Accept': '*/*'
        })
    
    def _get_base_url(self, region: str) -> str:
        """Get the appropriate API base URL for the region."""
        region_urls = {
            "SNYK-US-01": "https://api.snyk.io",
            "SNYK-US-02": "https://api.us.snyk.io", 
            "SNYK-EU-01": "https://api.eu.snyk.io",
            "SNYK-AU-01": "https://api.au.snyk.io"
        }
        return region_urls.get(region, "https://api.snyk.io")
    
    def get_token_details(self, version: str = "2024-10-15") -> Optional[Dict]:
        """Get details about the current token."""
        url = f"{self.base_url}/rest/self"
        params = {
            'version': version
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error fetching token details: {e}")
            return None
    
    def get_snyk_orgs(self, version: str = "2024-10-15", group_id: Optional[str] = None) -> List[Dict]:
        """Get all Snyk organizations."""
        url = f"{self.base_url}/rest/orgs"
        params = {
            'version': version,
            'limit': 100
        }
        
        if group_id:
            params['group_id'] = group_id
            
        all_orgs = []
        next_url = url
        next_params = params
        page = 1
        
        while next_url:
            print(f"   📄 Fetching orgs page {page}...")
            response = self.session.get(next_url, params=next_params)
            response.raise_for_status()
            data = response.json()
            
            orgs = data.get('data', [])
            all_orgs.extend(orgs)
            
            # Handle pagination
            links = data.get('links', {})
            next_url = links.get('next')
            next_params = None
            
            if next_url:
                if next_url.startswith('http'):
                    pass  # use as-is
                elif next_url.startswith('/'):
                    next_url = self.base_url + next_url
                else:
                    next_url = self.base_url + '/' + next_url.lstrip('/')
            else:
                next_url = None
            
            page += 1
        
        print(f"   ✅ Found {len(all_orgs)} total orgs")
        return all_orgs
    
    def get_targets_for_org(self, org_id: str, version: str = "2024-10-15", source_types: [List[str]] = None) -> List[Dict]:
        """
        Get all targets for a Snyk organization to preserve attributes.url.
        
        Args:
            org_id: Organization ID
            version: API version
            source_types: Optional list of source types to filter by (e.g., ['github', 'github-enterprise'])
            
        Returns:
            List of all targets with their URLs and metadata
        """
        print(f"🎯 Fetching all targets for organization {org_id}...")
        
        url = f"{self.base_url}/rest/orgs/{org_id}/targets"
        params = {
            'version': version,
            'limit': 100,
        }
        
  
        validated_source_types = validate_integration_types(source_types)
        if validated_source_types:
            # Join multiple source types with comma as expected by the API
            params['source_types'] = ','.join(validated_source_types)
            print(f"   🔍 Filtering by source types: {', '.join(validated_source_types)}")
        
        all_targets = []
        next_url = url
        next_params = params
        page = 1
        
        while next_url:
            print(f"   📄 Fetching targets page {page}...")
            response = self.session.get(next_url, params=next_params)
            response.raise_for_status()
            data = response.json()
            
            targets = data.get('data', [])
            all_targets.extend(targets)
            
            # Handle pagination
            links = data.get('links', {})
            next_url = links.get('next')
            next_params = None
            
            if next_url:
                if next_url.startswith('http'):
                    pass  # use as-is
                elif next_url.startswith('/'):
                    next_url = self.base_url + next_url
                else:
                    next_url = self.base_url + '/' + next_url.lstrip('/')
            else:
                next_url = None
            
            page += 1
        
        print(f"   ✅ Found {len(all_targets)} total targets")
        return all_targets
    
    
    def get_project_details(self, org_id: str, target_id: str, version: str = "2024-10-15") -> Optional[Dict]:
        """
        Fetch detailed information for a specific project, including branch information.
        
        Args:
            org_id: Organization ID
            version: API version for project details
            target_id: Target ID
        Returns:
            Dictionary containing the project details or None if failed
        """
        url = f"{self.base_url}/rest/orgs/{org_id}/projects"
        params = {
            'version': version,
            'target_id': target_id
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error fetching project details for project {target_id} with target {target_id}: {e}")
            return None
        
    def tag_project(self, org_id: str, project_id: str, tag_key: str, tag_value: str, existing_tags: List[Dict], owner_id: str, version: str = "2024-10-15", dry_run: bool = False) -> Optional[Dict]:
        """
        Tag a project with a default branch, preserving existing tags and settings.
        
        Args:
            org_id: Organization ID
            project_id: Project ID
            tag_key: Tag key for default branch
            tag_value: Tag value (default branch name)
            existing_tags: List of existing tags
            version: API version for tagging
            dry_run: If True, only simulate the action
            
        Returns:
            Success message or None if failed
        """
        if dry_run:
            # print(f"   🏃‍♂️ DRY RUN: Would tag project {project_id} with {tag_key}={tag_value}")
            return {"status": "dry_run"}
        
        url = f"{self.base_url}/rest/orgs/{org_id}/projects/{project_id}"
        params = {
            'version': version
        }
        
        # Prepare the updated tags list
        updated_tags = []
        tag_found = False
        
        # Check if the tag already exists
        for tag in existing_tags:
            if tag.get('key') == tag_key:
                # Tag exists, check if value is correct
                if tag.get('value') == tag_value:
                    print(f"   ✅ Tag {tag_key}={tag_value} already exists and is correct")
                    return {"status": "already_correct"}
                else:
                    print(f"   🔄 Updating existing tag {tag_key} from '{tag.get('value')}' to '{tag_value}'")
                    updated_tags.append({"key": tag_key, "value": tag_value})
                    tag_found = True
            else:
                # Keep other existing tags
                updated_tags.append(tag)
        
        # Add new tag if it doesn't exist
        if not tag_found:
            print(f"   ➕ Adding new tag {tag_key}={tag_value}")
            updated_tags.append({"key": tag_key, "value": tag_value})
        
        # Prepare the PATCH body with only the tags field
        body = {
            "data": {
                "type": "project",
                "id": project_id,
                "attributes": {
                    "tags": updated_tags
                },
                "relationships": {
                    "owner": {
                        "data": {
                            "id": owner_id,
                            "type": "user"
                        }
                    }
                }
            }
        }
        
        try:
            response = self.session.patch(url, params=params, json=body)
            response.raise_for_status()
            print(f"   ✅ Successfully tagged project {project_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error tagging project {project_id}: {e}")
            return None
    
    
class GithubAPI:
    """Github API client for collecting github default branch data."""
    
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        })
        # Store details of the last error for external consumers (e.g., error logger)
        self.last_error_details: Optional[Dict] = None
    
    def _record_github_error(self, details: Dict) -> None:
        """Record and print GitHub error details for diagnostics."""
        self.last_error_details = details
        status = details.get('status_code')
        msg = details.get('message') or details.get('response_text') or details.get('exception')
        if status:
            print(f"   ❌ GitHub API error (status {status}) for {details.get('url')}: {str(msg)[:500]}")
        else:
            print(f"   ❌ GitHub API error for {details.get('url')}: {str(msg)[:500]}")
    
    def extract_repo_info_from_url(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract repository owner and name from a GitHub URL.
        
        Args:
            url: GitHub repository URL (e.g., https://github.com/owner/repo.git)
            
        Returns:
            Dictionary with 'owner' and 'repo' keys, or None if URL is invalid
        """
        try:
            # Handle different GitHub URL formats
            if url.endswith('.git'):
                url = url[:-4]  # Remove .git suffix
            
            # Extract path from URL
            if 'github.com' in url:
                # Standard GitHub URL
                parts = url.split('github.com/')
                if len(parts) != 2:
                    return None
                path = parts[1]
            else:
                # GitHub Enterprise URL
                # Try to extract path after the domain
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path.lstrip('/')
            
            # Split path into owner and repo
            path_parts = path.split('/')
            if len(path_parts) >= 2:
                owner = path_parts[0]
                repo = path_parts[1]
                return {'owner': owner, 'repo': repo}
            
            return None
        except Exception as e:
            print(f"   ❌ Error parsing GitHub URL {url}: {e}")
            return None
    
    def get_default_branch(self, owner: str, repo: str) -> Optional[str]:
        """
        Get the default branch for a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Default branch name or None if failed
        """
        url = f"{self.base_url}/repos/{owner}/{repo}"
        
        try:
            response = self.session.get(url)
            # Capture non-200 responses with details without raising first
            if response.status_code != 200:
                details = {
                    'status_code': response.status_code,
                    'url': url,
                    'owner': owner,
                    'repo': repo,
                }
                try:
                    details['response_text'] = response.text
                    details['headers'] = dict(response.headers)
                except Exception:
                    pass
                self._record_github_error(details)
                return None
            data = response.json()
            return data.get('default_branch')
        except requests.exceptions.HTTPError as e:
            details = {
                'exception': type(e).__name__,
                'message': str(e),
                'url': url,
                'owner': owner,
                'repo': repo,
            }
            if getattr(e, 'response', None) is not None:
                details['status_code'] = e.response.status_code
                try:
                    details['response_text'] = e.response.text
                    details['headers'] = dict(e.response.headers)
                except Exception:
                    pass
            self._record_github_error(details)
            return None
        except requests.exceptions.RequestException as e:
            details = {
                'exception': type(e).__name__,
                'message': str(e),
                'url': url,
                'owner': owner,
                'repo': repo,
            }
            self._record_github_error(details)
            return None

    def get_repository_info(self, url: str) -> Optional[Dict[str, str]]:
        """
        Get repository information including default branch.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Dictionary with repository info or None if failed
        """
        repo_info = self.extract_repo_info_from_url(url)
        if not repo_info:
            return None
        
        default_branch = self.get_default_branch(repo_info['owner'], repo_info['repo'])
        if default_branch:
            return {
                'owner': repo_info['owner'],
                'repo': repo_info['repo'],
                'default_branch': default_branch,
                'url': url
            }
        
        return None


def main():
    parser = argparse.ArgumentParser(description="Tooling to tag Snyk projects with default branch data")
    parser.add_argument("--region", required=False, default="SNYK-US-01", help="Snyk region")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--key", required=True, help="Tag key for default branch Snyk projects")
    parser.add_argument("--value", required=True, help="Tag value for default branch Snyk projects")
    parser.add_argument("--integration-type", required=True, nargs='+', 
                       help="Integration type(s) for Snyk projects. Valid types: github, github-enterprise, github-cloud-app. "
                            "You can specify multiple types by separating them with spaces. Example: --integration-type github github-enterprise")
    parser.add_argument("--group-id", required=False, help="Snyk group ID")
    parser.add_argument("--github-base-url", required=False, default="https://api.github.com",
                       help="GitHub API base URL. Use https://api.github.com for GitHub.com or https://your-enterprise.com/api/v3 for GitHub Enterprise")
    parser.add_argument("--error-log", required=False, default="tagging_errors.log", help="Error log file path")
    args = parser.parse_args()
    
    # Initialize error logger
    error_logger = ErrorLogger(args.error_log)
    
    snyk_token = os.environ.get('SNYK_TOKEN')
    if not snyk_token:
        print("❌ Error: SNYK_TOKEN environment variable is required")
        sys.exit(1)
    
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable is required")
        sys.exit(1)
    
    # Validate integration types if provided
    source_types = None
    if args.integration_type:
        print(f"🔍 Processing integration types: {args.integration_type}")
        try:
            source_types = validate_integration_types(args.integration_type)
            print(f"✅ Validated integration types: {', '.join(source_types)}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            print(f"💡 Valid integration types are: {', '.join(VALID_INTEGRATION_TYPES)}")
            sys.exit(1)
    else:
        print("ℹ️  No integration types specified - will fetch all targets")
    
    print(f"🔧 Initializing Snyk API client (region: {args.region})...")
    snyk_api = SnykAPI(snyk_token, args.region)
    
    # Get token details to use as fallback for missing owner IDs
    print(f"🔍 Fetching token details...")
    token_details = snyk_api.get_token_details()
    fallback_user_id = None
    if token_details and 'data' in token_details:
        fallback_user_id = token_details['data']['id']
        print(f"✅ Token user ID: {fallback_user_id}")
    else:
        print(f"⚠️  Could not fetch token details - will skip projects with missing owner IDs")
    
    print(f"🔧 Initializing GitHub API client (base URL: {args.github_base_url})...")
    github_api = GithubAPI(github_token, args.github_base_url)
    
    print(f"🔍 Fetching Snyk organizations...")
    orgs = snyk_api.get_snyk_orgs(group_id=args.group_id)
    
    print(f"Amount of orgs: {len(orgs)}")
    
    # Process targets and get GitHub repository information
    if orgs:
        for org in orgs:
            print(f"\n🏢 Processing organization: {org['attributes']['name']} ({org['id']})")
            targets = snyk_api.get_targets_for_org(org['id'], source_types=source_types)
            print(f"Found {len(targets)} targets")
            
            for target in targets:
                target_url = target.get('attributes', {}).get('url')
                if target_url:
                    print(f"\n🔗 Processing target: {target_url}")
                    
                    # Get project details from Snyk
                    project_details = snyk_api.get_project_details(org['id'], target['id'])
                    # print(f"Project details: {json.dumps(project_details, indent=4)}")
                    
                    # Get repository information from GitHub
                    repo_info = github_api.get_repository_info(target_url)
                    if repo_info:
                        print(f"   ✅ Repository: {repo_info['owner']}/{repo_info['repo']}")
                        print(f"   🌿 Default branch: {repo_info['default_branch']}")
                        
                        # Check if project details exist and tag matching projects
                        if project_details and 'data' in project_details:
                            matching_projects = []
                            
                            # Find all projects that match the default branch
                            for project in project_details['data']:
                                if project['attributes']['target_reference'] == repo_info['default_branch']:
                                    matching_projects.append(project)
                            
                            if matching_projects:
                                print(f"   🎯 Found {len(matching_projects)} project(s) matching default branch '{repo_info['default_branch']}'")
                                
                                # Tag all matching projects
                                for project in matching_projects:
                                    project_id = project['id']
                                    existing_tags = project['attributes'].get('tags', [])
                                    
                                    print(f"   📝 Processing project: {project['attributes']['name']} ({project_id})")
                                    
                                    # Safely extract owner ID with error handling
                                    try:
                                        owner_id = project['relationships']['importer']['data']['id']
                                    except (KeyError, TypeError) as e:
                                        # Try to use fallback user ID from token
                                        if fallback_user_id:
                                            print(f"   🔄 Using fallback user ID from token: {fallback_user_id}")
                                            owner_id = fallback_user_id
                                        else:
                                            # Log the error and skip this project
                                            error_details = {
                                                'error': str(e),
                                                'project_id': project_id,
                                                'project_name': project['attributes'].get('name', 'Unknown'),
                                                'available_keys': list(project.get('relationships', {}).keys()) if project.get('relationships') else []
                                            }
                                            error_logger.log_error(
                                                'missing_owner_id',
                                                error_details,
                                                {
                                                    'project_id': project_id,
                                                    'project_name': project['attributes'].get('name', 'Unknown'),
                                                    'target_url': target_url,
                                                    'org_id': org['id'],
                                                    'org_name': org['attributes']['name']
                                                }
                                            )
                                            print(f"   ❌ Skipping project {project_id} - missing owner ID and no fallback available")
                                            continue
                                    
                                    # Tag the project with default branch information
                                    try:
                                        result = snyk_api.tag_project(
                                            org_id=org['id'],
                                            project_id=project_id,
                                            tag_key=args.key,
                                            tag_value=repo_info['default_branch'],
                                            existing_tags=existing_tags,
                                            owner_id=owner_id,
                                            dry_run=args.dry_run
                                        )
                                        
                                        if result:
                                            if result.get('status') == 'dry_run':
                                                print(f"   🏃‍♂️ DRY RUN: Would tag project {project_id}")
                                            elif result.get('status') == 'already_correct':
                                                print(f"   ✅ Project {project_id} already has correct tag")
                                            else:
                                                print(f"   ✅ Successfully tagged project {project_id}")
                                        else:
                                            print(f"   ❌ Failed to tag project {project_id}")
                                            
                                    except Exception as e:
                                        # Log API errors
                                        error_details = {
                                            'error': str(e),
                                            'project_id': project_id,
                                            'tag_key': args.key,
                                            'tag_value': repo_info['default_branch']
                                        }
                                        error_logger.log_error(
                                            'tagging_api_error',
                                            error_details,
                                            {
                                                'project_id': project_id,
                                                'project_name': project['attributes'].get('name', 'Unknown'),
                                                'target_url': target_url,
                                                'org_id': org['id'],
                                                'org_name': org['attributes']['name']
                                            }
                                        )
                                        print(f"   ❌ Error tagging project {project_id}: {e}")
                                        
                            else:
                                print(f"   ⚠️  No projects found matching default branch '{repo_info['default_branch']}'")
                        else:
                            # Log missing project details
                            error_details = {
                                'target_id': target['id'],
                                'target_url': target_url,
                                'project_details': project_details
                            }
                            error_logger.log_error(
                                'missing_project_details',
                                error_details,
                                {
                                    'target_url': target_url,
                                    'org_id': org['id'],
                                    'org_name': org['attributes']['name']
                                }
                            )
                            print(f"   ⚠️  No project details available for target")
                    else:
                        # Log GitHub API errors
                        gh_details = github_api.last_error_details or {}
                        error_details = {
                            'target_url': target_url,
                            'error': 'Could not extract repository information'
                        }
                        # Merge any captured GitHub details (status_code, response_text, headers, url, owner, repo)
                        try:
                            error_details.update(gh_details)
                        except Exception:
                            pass
                        error_logger.log_error(
                            'github_api_error',
                            error_details,
                            {
                                'target_url': target_url,
                                'org_id': org['id'],
                                'org_name': org['attributes']['name']
                            }
                        )
                        print(f"   ❌ Could not extract repository information from URL")
                else:
                    # Log targets without URLs
                    error_details = {
                        'target_id': target.get('id', 'Unknown'),
                        'target_attributes': target.get('attributes', {})
                    }
                    error_logger.log_error(
                        'missing_target_url',
                        error_details,
                        {
                            'target_id': target.get('id', 'Unknown'),
                            'org_id': org['id'],
                            'org_name': org['attributes']['name']
                        }
                    )
                    print(f"   ⚠️  Target has no URL attribute")
            
            print(f"✅ Completed processing {len(targets)} targets for organization {org['attributes']['name']}")
    
    # Save error log and show summary
    error_logger.save_log()
    
    # Show error summary
    error_summary = error_logger.get_summary()
    if error_summary:
        print(f"\n📊 Error Summary:")
        for error_type, count in error_summary.items():
            print(f"   {error_type}: {count} errors")
    
    # print(f"🔍 Fetching Snyk projects...")
    # projects = snyk_api.get_snyk_projects()


if __name__ == '__main__':
    main() 