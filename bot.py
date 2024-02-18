import logging
from flask import Flask

app = Flask(__name__)

# Configure logging to print requests to the console
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    app.logger.info('Received request to index')
    return 'Your Flask application is running!'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
