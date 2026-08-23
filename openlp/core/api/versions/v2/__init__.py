# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################

from openlp.core.api.versions.v2.controller import controller_views
from openlp.core.api.versions.v2.core import core
from openlp.core.api.versions.v2.service import service_views
from openlp.core.api.versions.v2.plugins import plugins, alert_1_views, alert_2_views


def register_blueprints(app):
    app.register_blueprint(controller_views, url_prefix='/api/v2/controller/')
    app.register_blueprint(core, url_prefix='/api/v2/core/')
    app.register_blueprint(service_views, url_prefix='/api/v2/service/')
    app.register_blueprint(plugins, url_prefix='/api/v2/plugins/')
    app.register_blueprint(alert_2_views, url_prefix='/api/v2/plugins/alerts')
    app.register_blueprint(alert_1_views, url_prefix='/api/alert')
