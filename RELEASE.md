# Release Guide for logerr

This document outlines the complete process for releasing logerr to PyPI.

## 🔍 Pre-Release Checklist

Before starting the release process, ensure all these steps are completed:

### 1. Code Quality & Testing
```bash
# Run all quality checks - ALL MUST PASS
pixi run -e dev check-all

# This runs:
# - pytest tests/ --doctest-modules logerr --cov=logerr --cov-report=term
# - mypy logerr  
# - ruff check logerr tests && ruff format --check logerr tests
```

### 2. Version Management
- Update version in `pyproject.toml`
- Update version in `logerr/__init__.py`
- Update any version references in `README.md`

### 3. Documentation
- Ensure README.md is up to date
- Check that all examples in README work
- Verify API documentation is current

### 4. Security Review
- ✅ **Completed**: No vulnerabilities found in codebase
- No hardcoded secrets or credentials
- All dependencies are secure and up to date

## 🚀 PyPI Release Process

### Step 1: PyPI Account Setup

#### Create Accounts (if not already done)
- **TestPyPI**: https://test.pypi.org/account/register/
- **PyPI**: https://pypi.org/account/register/

Both accounts require:
- Email verification
- 2FA enabled (required for token generation)

#### Generate API Tokens
1. **TestPyPI Token**: https://test.pypi.org/manage/account/token/
2. **PyPI Token**: https://pypi.org/manage/account/token/

Create tokens with "Entire account" scope or project-specific scope.

### Step 2: Configure Authentication

Create `~/.pypirc`:
```ini
[distutils]
index-servers = 
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

**Security Note**: Keep these tokens secure and never commit them to version control.

### Step 3: Build Packages

Due to Python 3.13 compatibility issues with the current build environment, use one of these methods:

#### Option A: System Python (Recommended)
```bash
# Install build tools
pip install build twine

# Clean previous builds
rm -rf dist/* build/* *.egg-info/

# Build packages
python -m build

# Verify build contents
python -m zipfile -l dist/*.whl
```

#### Option B: Alternative Build Method
```bash
# If you have working packages from a previous build
git checkout HEAD~1 -- dist/  # Restore if needed

# Or use setuptools directly
python setup.py sdist bdist_wheel
```

### Step 4: Validate Packages
```bash
# Check package integrity
twine check dist/*

# Should output: "Checking distribution dist/logerr-X.X.X.tar.gz: Passed"
#                "Checking distribution dist/logerr-X.X.X-py3-none-any.whl: Passed"
```

### Step 5: Test Release (TestPyPI)

**Always test on TestPyPI first!**

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Verify upload at: https://test.pypi.org/project/logerr/
```

#### Test Installation from TestPyPI
```bash
# Create a test environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ logerr

# Test basic functionality
python -c "
from logerr import Ok, Err, Some, Nothing, configure
print('✅ Basic imports successful')

# Test core functionality
result = Ok(42).map(lambda x: x * 2)
assert result.unwrap() == 84
print('✅ Core functionality works')

# Test optional recipes (if available)
try:
    from logerr.recipes import retry
    print('✅ Recipes module available')
except ImportError:
    print('ℹ️ Recipes module not available (optional)')

print('🎉 Package installation successful!')
"

# Clean up
deactivate
rm -rf test_env
```

### Step 6: Production Release (PyPI)

**Only after TestPyPI testing is successful:**

```bash
# Upload to production PyPI
twine upload dist/*

# Verify at: https://pypi.org/project/logerr/
```

### Step 7: Post-Release Tasks

1. **Create Git Tag**:
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   git push origin v0.1.0
   ```

2. **Update Documentation**:
   - Update installation instructions if needed
   - Publish documentation updates

3. **Announce Release**:
   - GitHub release notes
   - Update project status badges if needed

## 🔧 Using Pixi Commands

If the build environment issues are resolved, you can use the configured pixi commands:

```bash
# Build package
pixi run -e dev build

# Upload to TestPyPI
pixi run -e dev twine upload --repository testpypi dist/*

# Upload to PyPI  
pixi run -e dev distribute
```

## 📋 Package Contents Verification

Your wheel should include:
- `logerr/` - Main package
- `logerr/recipes/` - Optional functionality
- `*.pyi` - Type stub files
- `py.typed` - PEP 561 marker file

Verify with:
```bash
python -m zipfile -l dist/logerr-*.whl
```

Expected structure:
```
logerr/__init__.py
logerr/__init__.pyi
logerr/config.py
logerr/config.pyi
logerr/option.py
logerr/option.pyi
logerr/result.py  
logerr/result.pyi
logerr/utils.py
logerr/utils.pyi
logerr/protocols.py
logerr/protocols.pyi
logerr/py.typed
logerr/recipes/__init__.py
logerr/recipes/config.py
logerr/recipes/retry.py
logerr/recipes/retry.pyi
logerr/recipes/utilities.py
logerr/recipes/dataframes/...
```

## 🚨 Troubleshooting

### Build Issues
- **Python 3.13 compatibility**: Use system Python instead of pixi environment
- **Missing files**: Check `tool.setuptools.package-data` in `pyproject.toml`
- **Type stubs**: Ensure `.pyi` files are included

### Upload Issues
- **Authentication**: Verify API tokens in `~/.pypirc`
- **403 Forbidden**: Check token permissions and 2FA
- **Version conflicts**: Ensure version number is incremented

### Installation Issues
- **Import errors**: Check package structure and dependencies
- **Type checking**: Verify `py.typed` file is included

## 📚 References

- [Python Packaging Guide](https://packaging.python.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [TestPyPI](https://test.pypi.org/)
- [PyPI](https://pypi.org/)
- [PEP 561 - Type Stubs](https://www.python.org/dev/peps/pep-0561/)