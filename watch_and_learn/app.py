from re import findall
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
# Ran "pip3 install googletrans==3.1.0a0" in terminal to download Google Translate
from googletrans import Translator

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///watchnlearn.db")

# Initiate Google API translator
translator = Translator()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show homepage"""
    return render_template("index.html")


@app.route("/guide")
@login_required
def guide():
    """Show instructions"""
    return render_template("guide.html")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():
    """Show history of inputs"""

    user = session["user_id"]

    # When the URL shows a text_id (when user clicks view button in card)
    if request.args.get("text_id"):

        # Store text_id in a variable
        selected_text_id = request.args.get("text_id")

        # Search for stored data of text_id
        selected_list = []
        selected = db.execute("SELECT * FROM history WHERE (text_id = ?) AND (user_id = ?)", selected_text_id, user)

        # Put stored data into list to display on page
        for i in selected:
            word = i["word"]
            occurrence = i["occurrence"]
            translation = i["translation"]
            percentage = i["percentage"]

            # Check if word already focus or learned
            greencheck = 0
            if i["learnedflag"] > 0:
                greencheck = 1
            if i["focusflag"] > 0:
                greencheck = 1

            # Input table cell values into list to display
            selected_list.append([{"word": word}, {"occurrence": occurrence}, {"translation": translation}, {"percentage": percentage}, {"greencheck": greencheck}])

        # Find text title to display on page
        selected_title = selected[0]["text_name"]

        return render_template("history.html", selected_list=selected_list, selected_title=selected_title, greencheck=greencheck)

    # User chose to delete history - done via POST
    elif request.method == "POST":
        text_id = request.form.get("delete")
        db.execute("DELETE FROM history WHERE (text_id = ?) AND (user_id = ?)", text_id, user)
        db.execute("DELETE FROM text WHERE (text_id = ?) AND (user_id = ?)", text_id, user)

        # Return refreshed history page
        return redirect("/history")

    # Show cards of entries
    else:

        # Create empty list to store lists of dicts
        list = []

        # Search up history in database - INNER JOIN text_id, text_name, and text
        buffer = db.execute("SELECT DISTINCT history.text_id, history.text_name, text.text FROM history INNER JOIN text ON history.text_id = text.text_id WHERE history.user_id = ?", user)

        # If no history yet, return error
        if len(buffer) == 0:
            return apology("no history found", 401)

        # Store values into list
        for i in buffer:
            text_name = i["text_name"]
            text_id = i["text_id"]

            # Split up the input text at the 636th char
            text = i["text"]

            text1_list = []
            text2_list = []

            counter1 = 0
            counter2 = 0

            for i in text:
                text1_list.append(i)
                counter1 += 1
                if counter1 > 636:
                    break

            for i in text:
                counter2 += 1
                if counter2 > 637:
                    text2_list.append(i)

            text1 = ""
            text2 = ""

            text1 = text1.join(text1_list)
            text2 = text2.join(text2_list)

            # Input table cell values into list to display
            list.append([{"text_name": text_name}, {"text_id": text_id}, {"text1": text1}, {"text2": text2}])

        # Return cards display while in GET
        return render_template("historyhome.html", list=list)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 402)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 404)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    """Get text analysis."""

    if request.method == "POST":

        # Get current user's id
        user = session["user_id"]

        # Store user's inputs
        input = request.form.get("input")
        text_name = request.form.get("text_name")

        # Strip text name of leading/trailing spaces
        text_name = text_name.strip()

        # Check if user got input title
        if not text_name:
            return apology("missing transcript name", 405)

        # Check if user got input text
        if not input:
            return apology("missing transcript text", 406)

        # Check if input text is already in database - all but text_id in table <text> have to equal
        check_text = db.execute("SELECT * FROM text WHERE (user_id = ?) AND (text_name = ?) AND (text = ?)", user, text_name, input)

        # Using above found text_id, retrieve and show previous results
        if len(check_text) > 0:
            # Retrieve results by text_id and user_id
            output = db.execute("SELECT * FROM history WHERE (user_id = ?) AND (text_id = ?) AND (text_name = ?)", user, check_text[0]["text_id"], text_name)
            # Render template of analyzed text
            return render_template("analyzed.html", output=output, text_name=text_name)

        # Assign an id to the text
        toget_textid = db.execute("SELECT COUNT(DISTINCT text_id) FROM history WHERE user_id = ?", user)
        text_id = toget_textid[0]["COUNT(DISTINCT text_id)"]

        # Store input text into text table
        db.execute("INSERT INTO text (user_id, text_id, text_name, text) VALUES (?, ?, ?, ?)", user, text_id, text_name, input)

        # Count total words in text
        total_words = len(input.split())

        # Generate list of all words
        temp_words = findall(r"[\w`‘’'-]+", input)

        # Make each item lowercase and then put distinct in new list
        words = []
        all_words = []

        for item in temp_words:
            if item == "-" or item == "`" or item == "‘" or item == "’" or item == "'":
                continue
            item = item.lower()
            all_words.append(item)
            if not item in words:
                words.append(item)

        # Loop through each unique word
        for item in words:

            # Check if word already has existing id
            check_id = db.execute("SELECT word_id FROM history WHERE (word = ?) AND (user_id = ?)", item, user)
            if len(check_id) >= 1:
                word_id = check_id[0]["word_id"]
            else:
                word_id = len(db.execute("SELECT word_id FROM history")) + 1

            # Generate google translation for each word
            translation = translator.translate(item, dest="ko")

            # Count occurrence of word within input text
            occurrence = 0
            for i in all_words:
                if item == "-" or item == "`" or item == "‘" or item == "’" or item == "'":
                    continue
                if item == i:
                    occurrence += 1

            # Calculate percentage (divide occurrence by total words)
            percentage = occurrence / total_words * 100

            # Check word is already focused/learned from previous analyses
            focusflag = 0
            focuschecking = db.execute("SELECT * FROM history WHERE (user_id = ?) AND (word = ?) AND (focusflag = 1)", user, item)
            if len(focuschecking) > 0:
                focusflag = 1
            learnedflag = 0
            learnedchecking = db.execute("SELECT * FROM history WHERE (user_id = ?) AND (word = ?) AND (learnedflag = 1)", user, item)
            if len(learnedchecking) > 0:
                learnedflag = 1

            # Insert into table all values PER WORD
            db.execute("INSERT INTO history (user_id, text_id, text_name, word_id, word, translation, occurrence, percentage, focusflag, learnedflag) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", user, text_id, text_name, word_id, item, translation.text, occurrence, percentage, focusflag, learnedflag)

        # Populate output list to transfer over
        output = db.execute("SELECT * FROM history WHERE (user_id = ?) AND (text_id = ?)", user, text_id)

        # Render template of analyzed text
        return render_template("analyzed.html", output=output, text_name=text_name)

    else:
        # Render template of normally asking for input
        return render_template("analyze.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        passconf = request.form.get("confirmation")

        # Check if password confirmation is equal
        if password != passconf:
            return apology("passwords don't match", 407)

        # Check if username is taken already
        rows = db.execute("SELECT username FROM users WHERE username = ?", username)
        if len(rows) != 0:
            return apology("username's already taken", 408)

        # Check if password field is filled
        if not password:
            return apology("missing password", 409)

        # Check if username field is filled
        if not username:
            return apology("missing username", 410)

        # Hash password
        hashed = generate_password_hash(password)

        # Insert new user into database <users> table
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hashed)

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/focus", methods=["GET", "POST"])
@login_required
def focus():
    """Allow user to study selected words with flashcards"""

    # Store user number in variable
    user = session["user_id"]

    # User came here after submitting add something on either History/Analyzed/Progress or Focus page
    if request.method == "POST":

        # Store list of selected words into variable
        tomove = request.form.getlist("tomove")

        # If no value selected, return error
        if len(tomove) == 0:
            return apology("no words selected", 411)

        # Checking where user came from - focus or history/analyzed/progress
        tolearned_counter = 0
        tofocus_counter = 0
        # Check if every word has signal phrase "to_move_to_x"
        for item in tomove:
            if "to_move_to_learned" in item:
                tolearned_counter += 1
            if "to_move_to_focus" in item:
                tofocus_counter += 1

        # Check if user came from submitting ***ON FOCUS PAGE***
        if tolearned_counter == len(tomove):
            # If yes, then REMOVE from focus and ADD to learned
            for item in tomove:
                # Remove signal phrase first
                item = item.replace(" to_move_to_learned", "")
                # Remove from focus
                db.execute("UPDATE history SET focusflag = 0 WHERE (word = ?) AND (user_id = ?)", item, user)
                # Add to learned
                db.execute("UPDATE history SET learnedflag = 1 WHERE (word = ?) AND (user_id = ?)", item, user)
            # Return refreshed page
            return redirect("/focus")

        # Check if user came from submitting ***ON HISTORY/ANALYZED/PROGRESS PAGE***
        if tofocus_counter == len(tomove):
            # If yes, then ADD to focus pile
            for item in tomove:
                # Remove signal phrase first
                item = item.replace(" to_move_to_focus", "")
                # Add to focus
                db.execute("UPDATE history SET focusflag = 1 WHERE (word = ?) AND (user_id = ?)", item, user)
                # Remove from learned
                db.execute("UPDATE history SET learnedflag = 0 WHERE (word = ?) AND (user_id = ?)", item, user)
            # Return refreshed page
            return redirect("/focus")

    # User chose to remove word from Focus pile - submitted on Focus page
    elif request.args.get("word_id"):
        toremove_wordid = request.args.get("word_id")
        db.execute("UPDATE history SET focusflag = 0 WHERE (word_id = ?) AND (user_id = ?)", toremove_wordid, user)
        # Return refreshed page
        return redirect("/focus")

    # User came from clicking on Focus page in navbar
    else:

        # Select out focused in db for user
        focusflagged = db.execute("SELECT DISTINCT word FROM history WHERE (focusflag = 1) AND (user_id = ?)", user)

        # If nothing in focus, exit and return error
        if len(focusflagged) == 0:
            return apology("no words flagged for focus", 412)

        # Create list of flagged words
        focuswords = []
        for item in focusflagged:
            focuswords.append(item["word"])

        # Create output list to transfer over and display
        output = []

        # Go through each flagged word
        for item in focuswords:
            # Create empty list to store all appearances of word
            textnames = []
            # Find the text id FIRST
            textids = db.execute("SELECT text_id FROM text WHERE text LIKE ?", ("%" + item + "%"))
            # THEN go through each text id and find the text name
            for id in textids:
                name = db.execute("SELECT DISTINCT text_name FROM history WHERE (text_id = ?) AND (user_id = ?)", id["text_id"], user)
                # Put it in the empty list to store all appearances of word
                for title in name:
                    textnames.append(title["text_name"] + ", ")
            # Remove last item's comma
            textnames[-1] = textnames[-1].replace(",", "")

            # Find the translation of specified word
            translation = db.execute("SELECT DISTINCT translation FROM history WHERE word = ?", item)

            # Find ID of specified word
            word_id = db.execute("SELECT DISTINCT word_id FROM history WHERE (user_id = ?) AND (word = ?)", user, item)

            # Append it all onto output list to transfer over and display
            output.append([{"texts":textnames}, {"word":item}, {"translation":translation[0]["translation"]}, {"word_id":word_id[0]["word_id"]}])

        # Return normal display of focus words
        return render_template("focus.html", output=output)


@app.route("/progress")
@login_required
def progress():
    """Allow user to see percentage progress of transcripts"""

    user = session["user_id"]

    # Create empty list to transfer over later
    list = []

    # Search up user's text names
    buffer = db.execute("SELECT DISTINCT history.text_id, history.text_name, text.text FROM history INNER JOIN text ON history.text_id = text.text_id WHERE history.user_id = ?", user)

    # Search up user's learned words
    learnedwords = []
    buffer2 = db.execute("SELECT DISTINCT word_id, word FROM history WHERE (user_id = ?) AND (learnedflag = 1)", user)
    for item in buffer2:
        learnedwords.append(item["word"])

    # If no learned words yet, return error
    if len(learnedwords) == 0:
        return apology("no learned words found", 413)

    # Go through every text in history
    for i in buffer:
        # Counter (to use later) seeing how many words in text are learned
        learnedcounter = 0
        # Generate list of all words in text
        textwords = []
        textwords = findall(r"[\w'-]+", i["text"])
        # Loop through text words
        for item in textwords:
            # Remove non-words
            if item == "'" or item == "-":
                textwords.remove(item)
            # Loop through learned words
            for word in learnedwords:
                # If matched, count up
                if item == word:
                    learnedcounter += 1
        # Calculate percentage
        progress_percentage = float(learnedcounter / len(textwords) * 100)

        # Input values into list to display
        list.append([{"text_name": i["text_name"]}, {"progress": progress_percentage}])

    # Find data for learned words table in expandable card
    textnames = []
    output = []

    # Go through each flagged word
    for item in learnedwords:
        # Create empty list to store all appearances of word
        textnames = []
        # Find the text id FIRST
        textnames_finder = db.execute("SELECT text_name FROM text WHERE (user_id = ?) AND (text LIKE ?)", user, ("%" + item + "%"))
        # THEN go through each text id and find the text name
        for i in textnames_finder:
            textnames.append(i["text_name"] + ", ")
        # Remove last item's comma
        textnames[-1] = textnames[-1].replace(",", "")

        # Find the translation of specified word
        translation = db.execute("SELECT DISTINCT translation FROM history WHERE word = ?", item)

        # Find ID of specified word
        word_id = db.execute("SELECT DISTINCT word_id FROM history WHERE (user_id = ?) AND (word = ?)", user, item)

        # Append it all onto output list to transfer over and display
        output.append([{"texts":textnames}, {"word":item}, {"translation":translation[0]["translation"]}, {"word_id":word_id[0]["word_id"]}])

    return render_template("progress.html", list=list, output=output)