# Install this bruh #

```pip install undetected-chromedriver fake-useragent selenium webdriver-manager requests```



# Update packages
```pkg update && pkg upgrade -y```

# Install Python and essential tools
```pkg install python python-pip git wget -y```

# Install Chromium browser
```pkg install chromium -y```

# Install required Python packages
```pip install selenium requests webdriver-manager```

# Optional: Install undetected-chromedriver for better anti-detection
```pip install undetected-chromedriver```

# Optional: Install fake-useragent
```pip install fake-useragent```

# Optional: Install 2Captcha support
```pip install twocaptcha```

# Clone or download the script
# Create profiles file
```echo "https://facebook.com/profile1,harassment" > profiles.txt```
```echo "https://facebook.com/profile2,fake_account" >> profiles.txt```

# Run the script
```python fb_reporter.py -e "your_email@example.com" -p "your_password" -f profiles.txt```



# If Chromium not found
```pkg install chromium -y```

# If permission issues
```termux-setup-storage```

# If Python package issues
```pip install --upgrade pip```
```pip install selenium requests```




# If undetected-chromedriver fails
```pip install --upgrade undetected-chromedriver```

# If ChromeDriver issues
```pip install --upgrade webdriver-manager```
