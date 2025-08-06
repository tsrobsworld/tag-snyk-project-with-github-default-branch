# Snyk Default Branch Tagger

A robust Python tool for automatically tagging Snyk projects with their default branch information from GitHub. This tool fetches default branch data from GitHub repositories and applies it as tags to corresponding Snyk projects.

## 🎯 **Features**

- ✅ **Multiple Integration Types**: Support for GitHub, GitHub Enterprise, and GitHub Cloud App
- ✅ **GitHub Enterprise Support**: Custom base URL configuration for enterprise instances
- ✅ **Smart Tag Management**: Adds new tags, updates existing ones, preserves other tags
- ✅ **Error Logging**: Comprehensive error handling with detailed logging
- ✅ **Fallback User ID**: Uses authenticated user's ID when project owner ID is missing
- ✅ **Dry Run Mode**: Safe testing without making changes
- ✅ **Multiple Organizations**: Process all organizations or filter by group ID

## 📋 **Prerequisites**

- Python 3.7+
- Snyk API token
- GitHub API token
- Network access to Snyk and GitHub APIs

## 🔧 **Installation**

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd tag-snyk-project-with-default-branch
   ```

2. **Set up environment variables:**
   ```bash
   export SNYK_TOKEN="your-snyk-api-token"
   export GITHUB_TOKEN="your-github-api-token"
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirememts.txt
   ```

## 🚀 **Usage**

### **Basic Usage**

```bash
# Tag projects with default branch info
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main

# Dry run to test without making changes
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --dry-run
```

### **GitHub Enterprise**

```bash
# GitHub Enterprise with custom base URL
python snyk_default_branch_tagger.py --integration-type github-enterprise --key default-branch --value master --github-base-url https://github-enterprise.company.com/api/v3
```

### **Multiple Integration Types**

```bash
# Process both GitHub and GitHub Enterprise projects
python snyk_default_branch_tagger.py --integration-type github github-enterprise --key branch --value main
```

### **Advanced Options**

```bash
# With Snyk group ID and custom error log
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --group-id your-group-id --error-log my_errors.log

# Different Snyk region
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --region SNYK-EU-01
```

## 📖 **Command Line Arguments**

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--integration-type` | Yes | - | Integration type(s): github, github-enterprise, github-cloud-app |
| `--key` | Yes | - | Tag key for default branch projects |
| `--value` | Yes | - | Tag value for default branch projects |
| `--region` | No | SNYK-US-01 | Snyk region (SNYK-US-01, SNYK-US-02, SNYK-EU-01, SNYK-AU-01) |
| `--github-base-url` | No | https://api.github.com | GitHub API base URL |
| `--group-id` | No | - | Snyk group ID to filter organizations |
| `--error-log` | No | tagging_errors.log | Error log file path |
| `--dry-run` | No | False | Test mode without making changes |

## 🔍 **How It Works**

### **1. Authentication & Setup**
- Validates Snyk and GitHub tokens
- Fetches token details for fallback user ID
- Initializes API clients for both services

### **2. Organization Processing**
- Fetches Snyk organizations (optionally filtered by group ID)
- Processes each organization sequentially

### **3. Target & Project Processing**
- Fetches targets filtered by integration types
- For each target with a URL:
  - Extracts repository info from GitHub
  - Gets default branch from GitHub API
  - Fetches Snyk project details
  - Finds projects matching the default branch

### **4. Tagging Process**
- **Smart Tag Management**:
  - Adds new tags if they don't exist
  - Updates existing tags if values are wrong
  - Preserves all other existing tags
  - Skips if tag already exists with correct value

### **5. Error Handling**
- **Fallback User ID**: Uses authenticated user's ID when project owner ID is missing
- **Comprehensive Logging**: Captures all errors with full context
- **Graceful Degradation**: Continues processing despite errors

## 🛡️ **Error Handling**

The tool includes robust error handling for various scenarios:

### **Error Types**
- **`missing_owner_id`**: Project missing importer/owner relationship data
- **`github_api_error`**: Could not extract repository info from GitHub
- **`missing_project_details`**: No project details returned from Snyk API
- **`tagging_api_error`**: Failed to tag project via Snyk API
- **`missing_target_url`**: Target has no URL attribute

### **Error Log**
- **Format**: JSON with detailed error information
- **Location**: Current working directory (default: `tagging_errors.log`)
- **Content**: Timestamp, error type, details, and project context

### **Error Summary**
At completion, the tool provides a summary of errors by type:
```
📊 Error Summary:
   missing_owner_id: 2 errors
   github_api_error: 1 errors
```

## 📊 **Example Output**

```
🔍 Fetching token details...
✅ Token user ID: [TOKEN_USER_ID]

🏢 Processing organization: My Organization (org-id)
Found 5 targets

🔗 Processing target: https://github.com/owner/repo.git
   ✅ Repository: owner/repo
   🌿 Default branch: main
   🎯 Found 3 project(s) matching default branch 'main'
   
   📝 Processing project: owner/repo:package.json (project-id-1)
   🔄 Using fallback user ID from token: [TOKEN_USER_ID]
   ✅ Successfully tagged project project-id-1
   
   📝 Processing project: owner/repo:src/main.js (project-id-2)
   ✅ Project project-id-2 already has correct tag

📝 Error log saved to: tagging_errors.log
   Total errors logged: 1

📊 Error Summary:
   github_api_error: 1 errors
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Required
export SNYK_TOKEN="your-snyk-api-token"
export GITHUB_TOKEN="your-github-api-token"

# Optional
export SNYK_REGION="SNYK-US-01"  # Default region
```

### **Snyk Regions**
- `SNYK-US-01`: US (default)
- `SNYK-US-02`: US Secondary
- `SNYK-EU-01`: Europe
- `SNYK-AU-01`: Australia

### **GitHub Base URLs**
- **GitHub.com**: `https://api.github.com`
- **GitHub Enterprise**: `https://your-enterprise.com/api/v3`

## 🚀 **Advanced Usage**

### **Batch Processing**
```bash
# Process all GitHub projects in a group
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --group-id your-group-id

# Process with custom error log
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --error-log batch_errors.log
```

### **Testing & Validation**
```bash
# Dry run to see what would be done
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --dry-run

# Test with specific region
python snyk_default_branch_tagger.py --integration-type github --key default-branch --value main --region SNYK-EU-01 --dry-run
```

### **Enterprise Setup**
```bash
# GitHub Enterprise with custom base URL
python snyk_default_branch_tagger.py --integration-type github-enterprise --key default-branch --value master --github-base-url https://github.company.com/api/v3

# Multiple integration types for enterprise
python snyk_default_branch_tagger.py --integration-type github-enterprise github-cloud-app --key branch --value develop --github-base-url https://github.company.com/api/v3
```

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Token Authentication Errors**
   - Verify `SNYK_TOKEN` and `GITHUB_TOKEN` are set correctly
   - Check token permissions and expiration

2. **API Rate Limits**
   - GitHub API has rate limits for unauthenticated requests
   - Ensure `GITHUB_TOKEN` is set for higher limits

3. **Missing Projects**
   - Check integration type filtering
   - Verify target URLs are accessible
   - Review error log for specific issues

4. **Tagging Failures**
   - Check Snyk API permissions
   - Verify project ownership
   - Review error log for details

### **Error Log Analysis**
```bash
# View error log
cat tagging_errors.log

# Parse with jq (if available)
jq '.[] | select(.error_type == "missing_owner_id")' tagging_errors.log
```

## 📈 **Monitoring & Alerting**

### **Success Metrics**
- Projects successfully tagged
- Error rate percentage
- Error types distribution

### **Error Thresholds**
- Monitor error log file size
- Alert if error rate exceeds threshold
- Track error types over time

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For issues and questions:
1. Check the error log for specific error details
2. Review the troubleshooting section
3. Open an issue with error log contents and command used

---

**Built with ❤️ for Snyk project management automation** 