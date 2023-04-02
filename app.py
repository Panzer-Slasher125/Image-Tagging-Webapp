import json
from flask import Flask, render_template, request, session
from flask_session.__init__ import Session
from wtforms import Form, BooleanField
from PIL import Image
from PIL.ExifTags import TAGS
import os

abspicturePath = "C:\\Users\\bob22\\OneDrive\\Pictures\\MEME MAKING"  # Make a symbolic link of this in static
picturePath = "static/hentai" # This folder either has to either be in /static OR it can be a (soft) symbolic link in static
port = 9001 # Port the server is hosted on. This will move to config eventually.
configFilePath = os.path.join("", "config.cfg")  # Need to do a check to verify if this exists, and if it doesn't make one
tagsPath = os.path.join("", "tags.json")  # The path to the tags file, this is probably just a file with a list inside
supportedFileTypes = ('.jpg', '.png', '.jpeg', '.jfif') # You can probably add more picture file types

# Basic checks to make sure stuff exists (basically first time setup stuff)
if not os.path.exists(picturePath):
    if not os.path.exists("static"):
        os.mkdir("static")
    errorstring = 'Make sure that the file exists. Do this cmd with admin: mklink /D "' + os.path.abspath(picturePath) + '" "' + os.path.abspath(abspicturePath + '"')
    raise Exception(errorstring)
if not os.path.exists(configFilePath):
    with open(configFilePath, 'a+') as p:
        print("Created Config File")
if not os.path.exists(tagsPath):
    with open(tagsPath, 'a+') as p:
        p.write("[]")
        print("Created Tags File")
if not os.path.exists(os.path.join(picturePath, "notjpeg")):
    os.makedirs(os.path.join(picturePath, "notjpeg"))

listofFiles = os.listdir(picturePath)
listofPics = listofFiles.copy()

# Remove all files that aren't pictures (need to remove duplicates that merely differ by filetype)
for i in listofFiles:
    if not i.lower().endswith(supportedFileTypes):
        listofPics.remove(i)

# Some initialization stuff for the server
app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = picturePath
WTF_CSRF_ENABLED = False # Prevents csrf protection nonsense --- from the docs: "You can disable it globally—though you really shouldn’t—with the configuration:"
Session(app)

# Updates the session's list (cookie?) with the list of all images in the folder
def updateList():
    listofFilesx = os.listdir(picturePath)
    listofPicsx = listofFilesx.copy()

    # Remove all files that aren't pictures (need to remove duplicates that merely differ by filetype)
    for i in listofFilesx:
        if not i.lower().endswith(supportedFileTypes):
            listofPicsx.remove(i)

    session['listofPics'] = listofPicsx


# Extracts Windows XP Keywords (Tags) for a specified image, and returns them as a list
def extractTags(imagePath):
    img = Image.open(imagePath)
    tagsstr = ""

    for (k, v) in img.getexif().items():
        if k in TAGS:
            if TAGS[k] == "XPKeywords":
                tagsstr = v.decode('utf-16')  # Tags are stored as utf-16 for some reason, means emoji tags are possible

    # Remove null characters
    tagsstr = tagsstr.replace("\x00", "")

    # Split the string into a list
    tags = tagsstr.split(";")

    return tags


# Updates the known tags json file with the passed list of tags. Returns the list of all known tags.
def updateTags(tags):
    # Open the list of tags, and add to the tags if the tag is new
    with open(tagsPath, 'r') as jsonData:
        knownTags:list = json.load(jsonData)

        for t in tags:
            if not t in knownTags and t != "":
                knownTags.append(t)

    with open(tagsPath, 'w') as jsonData:
        json.dump(knownTags, jsonData)

    return knownTags


# Updates an image with a new tag (or removes it if it already exists)
def tagImage(tag:str, imagePath:str):
    currentTags = extractTags(imagePath)
    extension = os.path.splitext(imagePath)[1]

    if not tag in currentTags:
        currentTags.append(tag)
    else:
        currentTags.remove(tag)

    img = Image.open(imagePath)
    exifDict = img.getexif()

    tagsstr = ';'.join((map(str,currentTags)))
    tagsstr = tagsstr.removeprefix(";")

    # I think 40094 is the windows xp keywords index.
    exifDict[40094] = tagsstr.encode('utf-16')

    img = img.convert("RGB")
    img.save(imagePath.replace(extension, ".JPG"), exif=exifDict)
    if extension != ".JPG":
        img.save(picturePath + "/notjpeg/" + session['listofPics'][session['tiddyIndex']], exif=exifDict)
    updateList()
    return imagePath.replace(extension, ".jpg")


# What's a class I honestly have no clue
class tagForm(Form):
     pass
# Returns a html form made of checkboxes
def createCheckboxes(knownTags:list, currentTags:list):
    form = tagForm
    for i in knownTags:
        boolean = 'no'
        if i in currentTags:
            boolean = 'checked'
        field = BooleanField(i, id=i)
        field.name = i
        field.default = boolean # This actually doesn't work I think because of html5
        setattr(field, 'value', False)
        setattr(form, i, field)

    return form(request.form)


# Main page
@app.route('/')
@app.route('/index')
def hello():
    return "Hello python!!! <br> <a href=/pics-test> Tiddy :D </a>"


# Where the magic happens.
@app.route('/pics-test', methods=['GET', 'POST'])
def pictures():
    # Clean up the file path
    filePathForwardSlash = picturePath.replace("\\", "/")

    # Initialize the variable(s?)
    if not session.get("tiddyIndex"):
        session['tiddyIndex'] = 0
        updateList()

    # Handle Form input, theres definitely better ways to do it.
    if request.method == "POST":
        if request.form.get('action1') == "Previous": # Go to the prev image
            session['tiddyIndex'] = session['tiddyIndex'] - 1
        elif request.form.get('action2') == "Next": # Next image
            session['tiddyIndex'] = session['tiddyIndex'] + 1
        elif None != request.form.get('Index'): # Go to specific image index
            session['tiddyIndex'] = int(request.form.get("Index"))
        else:
            pass

    # Make sure the index is always in the range (with 894 pics, 1000 maps to 106)
    if abs(session['tiddyIndex']) >= len(session['listofPics']):
        session['tiddyIndex'] = session['tiddyIndex'] % len(session['listofPics'])

    # Get the Image path as a string as its really annoying otherwise
    imagePath = filePathForwardSlash + "/" + session['listofPics'][session['tiddyIndex']]

    # This goes here because it needs the image path (updates tags from textbox)
    if request.method == "POST" and None != request.form.get('updateTag'):
        newimagePath = tagImage(request.form.get('updateTag'), imagePath)
    else:
        newimagePath = imagePath

    # Extract the tags from the image
    tags = extractTags(newimagePath)

    # Update the known tags and keep the list in memory
    knownTags = updateTags(tags)

    # Function to sort the tags based off first alphabetical character
    def sortFunc(e):
        alphabet = ('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z')
        i = 0
        while e[i].lower() not in alphabet:
            i = i + 1
            if i >= len(alphabet):
                i = 0
                break
        return e[i].lower()

    knownTags.sort(key=sortFunc) # This is way better to navigate when sorted

    # Change tags with the checkboxes
    if request.method == "POST" and request.form.get('tag_submit') == "Submit Tag Changes":
        for i in knownTags:
            if None != request.form.get(i):
                newimagePath = tagImage(i, imagePath)

    # Update the tags if they just changed via the checkboxes
    tags = extractTags(newimagePath)

    # Create the checkboxes to display on the webpage
    checkboxes = createCheckboxes(knownTags,tags)

    checkedTags = {}

    # This is for rendering red/blue text on the tags. I would use the checkboxes but I couldn't figure it out
    for i in knownTags:
        checkedTags[i] = False
        if i in tags:
            checkedTags[i] = True

    # Render the webpage
    return render_template("client.html", tiddy_pic=newimagePath, tiddy_index=session['tiddyIndex'], metadata=checkboxes, known_tags=knownTags, checked_Tags=checkedTags)


# Updates tags file with new tags and converts all pictures into jpeg (since PNG doesn't like tags)
@app.route('/updatejson')
def updateJson():
    updateList()
    filePathForwardSlash = picturePath.replace("\\", "/")
    for i, p in enumerate(session['listofPics']):
        path = filePathForwardSlash + "/" + session['listofPics'][i]
        tags = extractTags(path)
        updateTags(tags)

        extension = os.path.splitext(p)[1]
        if extension.upper() != ".JPG":
            img = Image.open(path)
            exifDict = img.getexif()
            img = img.convert("RGB")
            img.save(path.replace(extension, ".JPG"), exif=exifDict)
            if extension.upper() != ".JPG":
                os.rename(path, picturePath + "/notjpeg/" + session['listofPics'][i])
            updateList()
    return "I am having so much sex uoh <a href='/pics-test'>Go Back</a>"

# Run the app.
if __name__ == '__main__':
    app.run('localhost', port)