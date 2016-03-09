**Deploying the Release Notes Generator**

It's based on the Python web framework Django, so install that first.

http://docs.djangoproject.com/en/1.1/intro/install/

Sync the code from Perforce. You don't want to put these files where the webserver can serve them up; instead, you tell the django.wsgi file where to look for the app.

Edit the following files so the paths match yours:

release-notes/relnotes/settings.py

Edit this file, putting in valid logins/passwords for Perforce and Bugzilla (may be read-only users):
release-notes/relnotes/changesgrabber/models.py

**Debugging/Maintaining the Release Notes Generator**

From the release-notes/relnotes directory, run 'manage.py runserver'. This will create the database tables if they don't exist already, then run the webapp on the port it displays.

Just point your browser to the provided link, and you can try it out.

(I use WingIDE to code and debug this app. http://www.wingware.com/)
