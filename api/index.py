import sys
import os

# Ensure project root is in Python path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
os.chdir(root_dir)

# Auto-seed database on Vercel cold start
if os.environ.get('VERCEL'):
    os.environ['DATABASE_PATH'] = '/tmp/hostel.db'
    from database import DATABASE
    if not os.path.exists(DATABASE):
        import seed_data
        seed_data.seed()

from app import app

# Vercel entry point
app = app
