import os
import subprocess
import shutil

def deploy_site(business_slug: str, html_content: str) -> str:
    """
    Deploys a generated HTML site to GitHub Pages by saving it under /docs/sites/
    and pushing to the remote git repository.
    
    Returns the live URL: https://surprisemfstech.com/sites/{business_slug}.html
    """
    # 1. Ensure docs/sites directory exists
    docs_dir = os.path.join(os.getcwd(), "docs", "sites")
    os.makedirs(docs_dir, exist_ok=True)
    
    # 2. Write the HTML file
    file_name = f"{business_slug}.html"
    dest_path = os.path.join(docs_dir, file_name)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"   📂 Saved site to docs/sites/{file_name}")
    
    # 3. Add a CNAME file in docs/ if it doesn't exist to bind surprisemfstech.com
    cname_path = os.path.join(os.getcwd(), "docs", "CNAME")
    if not os.path.exists(cname_path):
        try:
            with open(cname_path, "w", encoding="utf-8") as f:
                f.write("surprisemfstech.com\n")
            print("   🌐 Created docs/CNAME for surprisemfstech.com")
        except Exception as e:
            print(f"   ⚠️ Failed to create docs/CNAME: {e}")
        
    # 4. Git add, commit, and push
    try:
        # Check if we are inside a git repo
        res = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
        if res.returncode == 0:
            # Git add
            subprocess.run(["git", "add", f"docs/sites/{file_name}"], capture_output=True)
            if os.path.exists(cname_path):
                subprocess.run(["git", "add", "docs/CNAME"], capture_output=True)
                
            # Check if there are staged changes to commit
            status = subprocess.run(["git", "status", "--porcelain", f"docs/sites/{file_name}"], capture_output=True, text=True)
            cname_status = subprocess.run(["git", "status", "--porcelain", "docs/CNAME"], capture_output=True, text=True)
            
            if status.stdout.strip() or cname_status.stdout.strip():
                commit_msg = f"deploy: sample site for {business_slug}"
                subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True)
                print("   📝 Committed changes to Git")
                
                # Git push
                print("   🚀 Pushing to GitHub...")
                push_res = subprocess.run(["git", "push"], capture_output=True, text=True)
                if push_res.returncode == 0:
                    print("   ✅ Pushed successfully to GitHub Pages!")
                else:
                    print(f"   ⚠️ Git push failed: {push_res.stderr.strip()}")
                    print("   ℹ️ Please run 'git push' manually to publish the site.")
            else:
                print("   ℹ️ No changes to commit (site is identical to published version)")
        else:
            print("   ⚠️ Not inside a git repository workspace")
            
    except Exception as e:
        print(f"   ⚠️ Git deploy failed: {e}")
        print("   ℹ️ Saved site locally. Make sure to commit and push the 'docs' folder to publish.")
        
    # Return the live URL
    return f"https://surprisemfstech.com/sites/{business_slug}.html"
