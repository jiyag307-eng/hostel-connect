from app import app
import os

# Auto-seed database on Vercel cold start
if os.environ.get('VERCEL'):
    from database import DATABASE
    if not os.path.exists(DATABASE):
        import seed_data
        seed_data.seed()

# Vercel entry point
app = app
