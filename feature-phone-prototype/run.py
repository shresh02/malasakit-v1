"""Using Twilio's Python Quickstart guide, found at
https://www.twilio.com/docs/quickstart/python/twiml
"""

from flask import Flask, url_for, send_from_directory, request
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__, static_url_path='')


@app.route("/", methods=['GET', 'POST'])
def hello_monkey():
    """Respond to incoming requests."""
    resp = VoiceResponse()
    resp.say("Welcome to Malasakit.")
    resp.play("%s%s" % (request.url, 'mp3/q01.mp3'))
    return str(resp)

@app.route('/mp3/<path:path>')
def send_mp3(path):
    print("asdf", path)
    return send_from_directory('mp3', path)

if __name__ == "__main__":
    app.run(debug=True)
