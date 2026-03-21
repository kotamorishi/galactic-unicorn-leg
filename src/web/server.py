"""Web server setup using microdot.

Creates and configures the microdot app with all routes.
"""

from lib.microdot import Microdot
from web import routes


def create_app(app_context):
    """Create and configure the microdot web application.

    Args:
        app_context: dict with references to shared components:
            - config_manager: config module
            - wifi_manager: WiFiManager instance
            - display_renderer: DisplayRenderer instance
            - audio_player: AudioPlayer instance
            - scheduler: Scheduler instance
            - system_hal: SystemInterface instance
    """
    app = Microdot()
    app.ctx = app_context

    routes.register(app)

    return app
