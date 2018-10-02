# Installation

## Requirements:
1. python >= 3.6 interpreter
2. packages listed in python_requirements.txt
3. A folder with writing permissions for app files.

## Django server set up instructions
1. Create virtual environment where all packages will be installed to
   and which will be used to run apps.  Use `-p python3` to enforce
   python3 enterpreter.

2. install required packages by

        pip install --prefix /path/to/virtualenv -r python_requirements.txt

3. install genontol package from a git repo

        pip install --prefix=/path/to/virtualenv -e git+https://github.com/mikpom/genontol.git#egg=genontol

4. add enronment varialbe GONET_DATA pointing to directory with
   writing permissions where django server will store its files and logs.
   This can be achieved for example by adding this line to
   `$HOME/.bashrc`

        export GONET_DATA="/path/to/data/folder"
    For production enrinoment other ways of specifying environment
    variable should be used. E.g. for nginx it can be
    `/etc/profile.d/django_vars.sh`.
    
    Alternatively this configuration parameter can also be specified
    in `secrets.json` file (see next section)

5. Some of the settings can be set inside `gonet/settings.py` file or
   stored in a `secrets.json` file – a json formatted file of the form
   `{"SETTING NAME":"SETTING VALUE"}` not to expose it in the source
   code. Settings which app tries to read from secrets.json are
   SECRET_KEY and email configuration. All of these settings are
   **optional**.

    Note that for production server
    its address should be added to ALLOWED_HOSTS setting.
   
6. From the base directory of the project run

        python manage.py makemigrations
        python manage.py migrate
    This should create sqlite database and all required tables.

7. Run tests

        python manage.py test
8. After this development server can be run with

        python manage.py runserver
and should be available in your browser at http://127.0.0.1:8000/GOnet .

## JavaScript building

During server runtime Javascript source is served from directory
`static/JavaScript/bundles` where corresponding bundles are
residing. The bundles are generated using Webpack. Root directory for
Webpack module is JavaScript folder you can find in projects root.

Javascript directory contains main Webpack configuration file
`webpack.config.js` and package.json file listing required packages.

To build bundles from Javascript directory run

    npx webpack --config webpack.config.js
    
To build budles for production use run 

    npx webpack --config webpack.config.js --mode production
    
This will got through the entry point JS files in Javascript folder
and output resulting bundles to `static/JavaScript/bundles`. All these
configurations are stored in `webpack.config.js`.
    

