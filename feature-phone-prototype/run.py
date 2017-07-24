"""Using Twilio's Python Quickstart guide, found at
https://www.twilio.com/docs/quickstart/python/twiml
"""

import urllib

from flask import Flask, url_for, send_from_directory, request
from twilio.twiml.voice_response import VoiceResponse

app = Flask(__name__, static_url_path='')


@app.route("/", methods=['GET', 'POST'])
def hello_monkey():
    """Respond to incoming requests."""
    resp = VoiceResponse()
    resp.say("Welcome to Malasakit.")
    resp.say("This is a survey in which you will be asked several questions. You will be asked to rate each response verbally by saying a number, zero to nine.")

    play_quant_question(resp, 1, 'q01.mp3')
    return str(resp)

@app.route('/mp3/<path:path>')
def send_mp3(path):
    print("asdf", path)
    return send_from_directory('mp3', path)

@app.route('/handle-recording', methods=['GET', 'POST'])
def handle_recording():
    resp = VoiceResponse()
    recording_url = request.values.get('RecordingUrl', None)
    user_response = urllib.URLopener()
    user_response.retrieve(recording_url, 'responses/response.mp3')
    resp.say("Response received.")
    return str(resp)


def play_quant_question(resp, question_id, question_path):
    resp.say("Please answer Question %s by saying a number from 0 to 9." % question_id)
    resp.play("%smp3/%s" % (request.url, question_path))
    resp.record(maxLength='3', action='/handle-recording')


if __name__ == "__main__":
    app.run(debug=True)
