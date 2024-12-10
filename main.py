from src.layout import get_layout
from src.app import app

if __name__ == '__main__':
    app.layout = get_layout()
    # app.run(debug=True)
    app.run_server(host = '0.0.0.0', debug = False)
