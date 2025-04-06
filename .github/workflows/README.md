# GitHub Actions CI/CD for mcp-client

This directory contains GitHub Actions workflows to automate the build and publishing process for the mcp-client package.

## publish.yml

This workflow builds and publishes the package to PyPI when a new tag is pushed.

### How to Use

1. **Set up PyPI tokens as repository secrets**:
   - Go to PyPI, create an API token for your account
   - Go to TestPyPI, create another API token for testing
   - Add these tokens as repository secrets in GitHub:
     - `PYPI_API_TOKEN`: Your PyPI API token
     - `TEST_PYPI_API_TOKEN`: Your TestPyPI API token

2. **Release process**:
   - Update version in `pyproject.toml` and `mcp_client/__init__.py`
   - Commit changes and push to GitHub
   - Create and push a new tag that matches the version:
   
   ```bash
   # Example for releasing v0.4.0
   git tag -a v0.4.0 -m "Release v0.4.0"
   git push origin v0.4.0
   ```

3. **Monitor the workflow**:
   - The workflow will run automatically when the tag is pushed
   - It will first publish to TestPyPI for verification
   - Then it will publish to PyPI if there are no issues

### Workflow Details

The workflow:
1. Checks out the repo
2. Sets up Python 3.8
3. Installs build dependencies
4. Builds the package
5. Validates the package with twine
6. Tests installation of the built package
7. Publishes to TestPyPI
8. Publishes to PyPI if it's a tag push

### Troubleshooting

- If the workflow fails, check the GitHub Actions logs
- Ensure your PyPI tokens are correctly set up
- Verify that your package version is incremented in `pyproject.toml` and `__init__.py`
- Make sure your package passes validation with twine 