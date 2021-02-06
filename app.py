import os
from datetime import datetime
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Check if the message is POST
    if request.method == "POST":
        # Check if email address exists in db
        existing_user = mongo.db.users.find_one(
            {"user_email_address": request.form.get(
                "email").lower()})

        # If it doesn't, display a flash message informing user that an account already exists for this email address.
        if existing_user:
            flash("Account already exists for this email address.")
            return redirect(url_for("register"))

        # Otherwise, assign form inputs (values) to keys and insert record into users collection.
        record = {
            "first_name": request.form.get("first-name").lower(),
            "last_name": request.form.get("last-name").lower(),
            "user_email_address": request.form.get("email").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(record)

        # Put the new users email address into session cookie and display flash success message using their first name.
        session["user_email_address"] = request.form.get("email").lower()
        flash("Registration successful")
        # Redirect to account(username) function where username is the users email address.
        return redirect(url_for(
            "account", username=session["user_email_address"]))

    # If method is not POST (i.e. GET) render register.html template.
    return render_template("register.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    # Check if the message is POST
    if request.method == "POST":
        # Check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"user_email_address": request.form.get(
                "email").lower()})

        # If user exists in database:
        if existing_user:
            # Ensure hashed password matches password input by user.
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    # If so then put the users email address into session cookie and display flash success message.
                    session["user_email_address"] = existing_user["user_email_address"].lower()
                    flash("Welcome back {}".format(
                        existing_user["first_name"].capitalize()))
                    # Redirect to account(username) function where username is the users email address.
                    return redirect(url_for(
                        "account", username=session["user_email_address"]))
            else:
                # If password doesn't match, display flash message informing the user and return them to a blank sign in page.
                flash("Incorrect Email Address and/or Password")
                return redirect(url_for("signin"))

        # If  email address doesn't exist in db, display flash message informing the user and return them to a blank sign in page.
        else:
            flash("Incorrect Email Address and/or Password")
            return redirect(url_for("signin"))

    # If method is not POST (i.e. GET) render register.html template.
    return render_template("signin.html")


@app.route("/account/<username>", methods=["GET", "POST"])
def account(username):
    # Use email address in session storage to search users collection.  Asign email address as username.
    username = mongo.db.users.find_one(
        {"user_email_address": session["user_email_address"]})["user_email_address"]
    # Use email address in session storage to search users collection.  Asign results to user.
    user = mongo.db.users.find_one(
        {"user_email_address": session["user_email_address"]})
    # Remove the users password.  Even though it is hashed, I don't want to pass this through.
    user.pop("password")
    # Use email address in session storage to search meter_installs collection.  Asign results to bookings.  Sort by install date and then address.
    bookings = list(mongo.db.meter_installs.find(
        {"user_email_address": session["user_email_address"]}).sort([("install_date", 1),("first_address_line", 1)]))

    # Check if there is a user email address saved in session variable, if so render account page.
    if session["user_email_address"]:
        # Render template.  Pass through the username, user and bookings variables defined above.
        return render_template(
            "account.html", 
            username=username,
            user=user,
            bookings=bookings)
    # If there is no user email address saved in session variable, redirect user to sign in page.
    return redirect(url_for("signin"))


@app.route("/signout")
def signout():
    # Remove the users email address from session cookies.
    flash("You have been signed out.")
    session.pop("user_email_address")
    return redirect(url_for("signin"))


@app.route("/book", methods=["GET", "POST"])
def book():
    # If method is POST (i.e. form submitted), add form data to meter installs collection.
    if request.method == "POST":
        # Check whether there is a meter install already booked for this meter ID.
        existing_booking = mongo.db.meter_installs.find_one(
            {"meter_id": request.form.get(
                "meter_id")})
        # If a record (booking) already exists for this meter ID, display a flash message to the user.
        if existing_booking:
            flash("A smart meter installation has already been booked for Meter ID "+ request.form.get("meter_id"))
        # Else extract data from form and assign to keys in the booking dictionary.
        else:
            # Check whether the supplier authorisation is selected and asign True if so, False if not.
            authorised = True if request.form.get(
                "supplier_authorisation")=="on" else False
            booking = {
                "user_email_address": session["user_email_address"],
                "meter_id": request.form.get("meter_id"),
                "meter_serial_number": request.form.get("meter_serial_number"),
                "first_address_line": request.form.get("first_address_line"),
                "second_address_line": request.form.get("second_address_line"),
                "third_address_line": request.form.get("third_address_line"),
                "town": request.form.get("town"),
                "county": request.form.get("county"),
                "postcode": request.form.get("postcode"),
                "meter_location": request.form.get("meter_location"),
                "access_instructions": request.form.get("access_instructions"),
                "parking_on_site": request.form.get("parking_on_site"),
                "property_type": request.form.get("property_type"),
                "supplier": request.form.get("supplier"),
                "supplier_acc_no": request.form.get("supplier_acc_no"),
                "meter_read_reg_1": request.form.get("meter_read_reg_1"),
                "meter_read_reg_2": request.form.get("meter_read_reg_2"),
                "install_date": datetime.strptime(request.form.get("install_date"), "%d/%m/%Y"),
                "supplier_authorisation": authorised,
                "application_date": datetime.now(),
                "installation_complete": False
            }
            # Insert the booking dictionary into the meter_installs collection.
            mongo.db.meter_installs.insert_one(booking)
            # Display a flash message informing user that booking has been successful.
            flash("Meter install successfully booked")
            # Redirect to account(username) function where username is the users email address.
            return redirect(url_for(
                "account", username=session["user_email_address"]))

    return render_template("book.html")


@app.route("/view_booking/<booking_id>")
def view_booking(booking_id):
    # Find the record with the corresponding booking ID in the meter_installs collection.
    booking = mongo.db.meter_installs.find_one({"_id": ObjectId(booking_id)})
    return render_template("view_booking.html", booking=booking)


@app.route("/delete_booking/<booking_id>")
def delete_booking(booking_id):
    # Find the booking in the meter_installs collection with the booking id that's been passed through and delete it.
    mongo.db.meter_installs.delete_one({"_id": ObjectId(booking_id)})
    # Display a flash message informing user that the booking has been deleted.
    flash("Your meter install booking has been deleted")
    # Redirect the user back to the account page.
    return redirect(url_for(
        "account", username=session["user_email_address"]))


@app.route("/update_booking/<booking_id>", methods=["GET", "POST"])
def update_booking(booking_id):
    # If method is POST (i.e. form submitted), update the data in the meter_installs collection.
    if request.method == "POST":
        # Retrieve the original booking from the meter_installs collection.
        original_booking = mongo.db.meter_installs.find_one({"_id": ObjectId(booking_id)})
        # Check whether the supplier authorisation is selected and asign True if so, False if not.
        authorised = True if request.form.get(
            "supplier_authorisation")=="on" else False
        # Asign form elements to keys in update dict.
        update = {
            "user_email_address": session["user_email_address"],
            "meter_id": request.form.get("meter_id"),
            "meter_serial_number": request.form.get("meter_serial_number"),
            "first_address_line": request.form.get("first_address_line"),
            "second_address_line": request.form.get("second_address_line"),
            "third_address_line": request.form.get("third_address_line"),
            "town": request.form.get("town"),
            "county": request.form.get("county"),
            "postcode": request.form.get("postcode"),
            "meter_location": request.form.get("meter_location"),
            "access_instructions": request.form.get("access_instructions"),
            "parking_on_site": request.form.get("parking_on_site"),
            "property_type": request.form.get("property_type"),
            "supplier": request.form.get("supplier"),
            "supplier_acc_no": request.form.get("supplier_acc_no"),
            "meter_read_reg_1": request.form.get("meter_read_reg_1"),
            "meter_read_reg_2": request.form.get("meter_read_reg_2"),
            "install_date": datetime.strptime(request.form.get("install_date"), "%d/%m/%Y"),
            "supplier_authorisation": authorised,
            "application_date": original_booking["application_date"],
            "installation_complete": False
        }
         # Check whether the meter_id has changed.
        if original_booking["meter_id"] != update["meter_id"]:
            # If so, check the meter_installs collection to see if another booking has been made with the updated meter_id.
            existing_booking = mongo.db.meter_installs.find_one(
                {"meter_id": update["meter_id"]})
            # If there is another meter found in the meter_installs collection.
            if existing_booking:
                # Display a flash message to the user advising them that there is an existing booking for the updated meter_id.
                flash("A smart meter installation has already been booked for Meter ID "+ request.form.get("meter_id"))
            else:
                # Otherwise, update the booking in the meter_installs collection.
                mongo.db.meter_installs.update({"_id": ObjectId(booking_id)}, update)
                # Display a flash message informing user that booking has been successfully updated.
                flash("Meter install booking updated")
                # Redirect to account(username) function where username is the users email address.
                return redirect(url_for(
                    "account", username=session["user_email_address"]))
        else:
            # If meter_id has not changed, then update  the booking in the meter_installs collection.
            mongo.db.meter_installs.update({"_id": ObjectId(booking_id)}, update)
            # Display a flash message informing user that booking has been successfully updated.
            flash("Meter install booking updated")
            # Redirect to account(username) function where username is the users email address.
            return redirect(url_for(
                "account", username=session["user_email_address"]))

    # Find the record with the corresponding booking ID in the meter_installs collection.
    booking = mongo.db.meter_installs.find_one({"_id": ObjectId(booking_id)})
    return render_template("update_booking.html", booking=booking)


@app.route("/update_account/<username>", methods=["GET", "POST"])
def update_account(username):
    # Use email address that's been passed through to search users collection.  Asign results to user.
    user = mongo.db.users.find_one(
        {"user_email_address": username})
    # If method is POST (i.e. form submitted), update the data in the meter_installs collection.
    if request.method == "POST":
        # Check that the password the user has entered matches the users password in the users collection.
        if check_password_hash(
            user["password"], request.form.get("password")):
            # If so, create update_user dict containing the updated details.  Password will be the existing hashed password.
            update_user = {
                "first_name": request.form.get("first-name").lower(),
                "last_name": request.form.get("last-name").lower(),
                "user_email_address": request.form.get("email").lower(),
                "password": user["password"]
            }
            # Update the existing record using the user id.
            mongo.db.users.update({"_id": ObjectId(user["_id"])}, update_user)
            # Check whether the user has updated their email address:
            if user["user_email_address"] != update_user["user_email_address"]:
                # If so, use the update_many method to find all meter_installs records with old email address and update to the new email address.
                # Solution reached referring to:  https://www.w3schools.com/python/python_mongodb_update.asp
                mongo.db.meter_installs.update_many({
                    "user_email_address": user["user_email_address"]
                    }, {
                        "$set": {
                            "user_email_address": update_user["user_email_address"]
                        },
                    }
                )
                # Update the users details in the users collection when the user has changed their email address.
                session["user_email_address"] = update_user["user_email_address"].lower()
            # Display flash message informing user that account details have been successfully updated.
            flash("Account details updated")
            # Redirect to account(username) function where username is the users email address.
            return redirect(url_for(
                "account", username=session["user_email_address"]))
        else:
            # If password doesn't match, display flash message informing the user and ask them to try again.  Redirect user back to update_account page.
            flash("Incorrect password - try again")
            return redirect(url_for("update_account", username=username))
    else:
        # Remove the users password.  Even though it is hashed, I don't want to pass this through for security reasons.
        user.pop("password")
        # Check if there is a user email address saved in session variable, if so render update_account page.
        if session["user_email_address"]:
            # Render template.  Pass through the username, user and bookings variables defined above.
            return render_template(
                "update_account.html", 
                user=user)
        # If there is no user email address saved in session variable, redirect user to sign in page.
        return redirect(url_for("signin"))


@app.route("/delete_account/<username>", methods=["POST"])
def delete_account(username):
    user = mongo.db.users.find_one({
        "username": username
    })
    # Check whether the user has provided the correct password.
    if check_password_hash(
            user["password"], request.form.get("password")):
        # If so, find bookings in meter_installs collection with corresponding user email address and delete them all.
        # Solution reached referring to: https://www.w3schools.com/python/python_mongodb_delete.asp
        mongo.db.meter_installs.delete_many({
            "user_email_address": username})
        # Find the users record in the users collection and delete it.  There will only be one record with corresponding email address so use delete_one method.
        mongo.db.users.delete_one({
            "user_email_address": username})
        # Delete the users email address out of session storage.
        session.pop("user_email_address")
        # Redirect user to the registration page and display flash message informing them that account and bookings have been deleted.
        flash("Your account and all meter install bookings have been deleted")
        return redirect(url_for(
            "register"))
    else:
        flash("Incorrect password - try again")
        return redirect(url_for(
                "account", username=session["user_email_address"]))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
