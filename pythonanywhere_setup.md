# Deploy on PythonAnywhere (FREE - No Credit Card)

## Step 1: Create Account
Go to https://www.pythonanywhere.com/registration/register/beginner/
Sign up (free "Beginner" plan)

## Step 2: Open Bash Console
After login → Go to "Consoles" tab → Click "$ Bash" under "Other"

## Step 3: Clone Your Repo
Run these commands one by one:

```bash
git clone https://github.com/jiyag307-eng/hostel-connect.git
cd hostel-connect
pip3 install --user flask werkzeug
python3 seed_data.py
```

## Step 4: Create Web App
1. Go to "Web" tab → Click "Add a new web app"
2. Click "Next" (accept the free domain yourname.pythonanywhere.com)
3. Select "Flask"
4. Select "Python 3.10"
5. Set source code path to: /home/YOURUSERNAME/hostel-connect/app.py
6. Click "Next"

## Step 5: Configure WSGI
1. On the Web tab, click the WSGI configuration file link
2. Replace ALL contents with:

```python
import sys
sys.path.insert(0, '/home/YOURUSERNAME/hostel-connect')
from app import app as application
```

3. Save the file

## Step 6: Reload
Click the green "Reload" button on the Web tab.

Your app is now live at: https://YOURUSERNAME.pythonanywhere.com

