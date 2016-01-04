
#Jama Software
Jama Software is the definitive system of record and action for product development. The company’s modern requirements and test management solution helps enterprises accelerate development time, mitigate risk, slash complexity and verify regulatory compliance. More than 600 product-centric organizations, including NASA, Boeing and Caterpillar use Jama to modernize their process for bringing complex products to market. The venture-backed company is headquartered in Portland, Oregon. For more information, visit [jamasoftware.com](http://jamasoftware.com).

Please visit [dev.jamasoftware.com](http://dev.jamasoftware.com) for additional resources and join the discussion in our community [community.jamasoftware.com](http://community.jamasoftware.com).

## Jama-SVN
Post-commit script which adds traceability from Jama to source code in Subversion.
Please note that this script is distrubuted as-is as an example and will likely require modification to work for your specific use-case.  It's been developer tested with VisualSVN for Windows. Jama Support will not assist with the use or modification of the script.

### Setup
1. Install [Python 2.x](https://www.python.org/) and the [requests](http://docs.python-requests.org/en/latest/) library.

2. As always, set up a test environment and project to test the script.

3. In your Jama admin section you'll need to create an item type. Call the item type whatever you want (commonly "Code Validation" or similar).  The only fields it needs are name and description, although it can have more.  Note your new item type's API ID before you move on.  

4. Create a set of your new items in your test project.  Note the set's name (usually "Code Validations").  Also create a set of some other item type, Requirements for example, and add a few items.

5. Complete the CONFIG section of the jama-svn.py script with your organization's information.  This is where you'll need the information from steps 2 and 3. 

6. Place the script in your SVN repository's /hooks/ directory and add a call to the script in your post-commit hook.
On Windows, add this line to your post-commit hook: 
```
{Path to Python executable}\python.exe %1\hooks\jama-svn.py %1 %2
```

### Testing

Make a commit to the Subversion repo containing the post-commit hook you modified.  Somewhere in the commit message put the Document Key of one of the Jama Requirement items.
```
svn commit -m "This is a test commit with a mention of TST-REQ-1"
```
Check the Jama Requirement item for a new downstream item.  The new item's type will be the type you created, and its description will include information about the commit you just made.  Additional commits with the same Document Key will cause the new commit's information to appear above older commits.

Post-commit scripts can be hard to debug, but if the script terminates with an exit code other than zero any text printed to stderr will propogate to the user.  Using this can help with some print statement debugging or error reporting.
```Python
sys.stderr.write(message_to_propogate)
sys.exit(1)
```
