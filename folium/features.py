# -*- coding: utf-8 -*-
"""
Features
------

A generic class for creating features.
"""
import warnings
from uuid import uuid4

from jinja2 import Environment, PackageLoader, Template
ENV = Environment(loader=PackageLoader('folium', 'templates'))
from collections import OrderedDict
import json

from .six import text_type, binary_type, urlopen


class Feature(object):
    """Basic feature object that does nothing.
    Other features may inherit from this one."""
    def __init__(self, template=None, template_name=None):
        """Creates a feature."""
        self._name = 'Feature'
        self._id = uuid4().hex
        self._env = ENV
        self._children = OrderedDict()
        self._parent = None
        self._template = Template(template) if template is not None\
            else ENV.get_template(template_name) if template_name is not None\
            else Template(u"""
        {% for name, feature in this._children.items() %}
            {{feature.render(**kwargs)}}
        {% endfor %}
        """)

    def add_children(self, child, name=None, index=None):
        """Add a children."""
        if name is None:
            name = text_type(child._name)+u"_"+text_type(child._id)
        if index is None:
            self._children[name] = child
        else:
            items = [item for item in self._children.items() if item[0] != name]
            items.insert(int(index),(name,child))
            self._children = items
        child._parent = self

    def add_to(self, parent, name=None, index=None):
        """Add feature to a parent."""
        parent.add_children(self, name=name, index=index)

    def to_dict(self, depth=-1, ordered=True, **kwargs):
        if ordered:
            dict_fun = OrderedDict
        else:
            dict_fun = dict
        out = dict_fun()
        out['name'] = self._name
        out['id'] = self._id
        if depth != 0:
            out['children'] = dict_fun([(name, child.to_dict(depth=depth-1))\
                    for name,child in self._children.items()])
        return out

    def to_json(self, depth=-1, **kwargs):
        return json.dumps(self.to_dict(depth=depth, ordered=True), **kwargs)

    def get_root(self):
        """Returns the root of the features tree."""
        if self._parent is None:
            return self
        else:
            return self._parent.get_root()

    def render(self, **kwargs):
        """TODO : docstring here."""
        return self._template.render(this=self, kwargs=kwargs)

_default_js = [
    ('leaflet',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.js"),
    ('jquery',
     "https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"),
    ('bootstrap',
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js"),
    ('awesome_markers',
     "https://rawgithub.com/lvoogdt/Leaflet.awesome-markers/2.0/develop/dist/leaflet.awesome-markers.js"),
    ('marker_cluster_src',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/leaflet.markercluster-src.js"),
    ('marker_cluster',
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/leaflet.markercluster.js"),
    ]

_default_css = [
    ("leaflet_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.3/leaflet.css"),
    ("bootstrap_css",
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap.min.css"),
    ("bootstrap_theme_css",
     "https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/css/bootstrap-theme.min.css"),
    ("awesome_markers_font_css",
     "https://maxcdn.bootstrapcdn.com/font-awesome/4.1.0/css/font-awesome.min.css"),
    ("awesome_markers_css",
     "https://rawgit.com/lvoogdt/Leaflet.awesome-markers/2.0/develop/dist/leaflet.awesome-markers.css"),
    ("marker_cluster_default_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.Default.css"),
    ("marker_cluster_css",
     "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/0.4.0/MarkerCluster.css"),
    ("awesome_rotate_css",
     "https://raw.githubusercontent.com/python-visualization/folium/master/folium/templates/leaflet.awesome.rotate.css"),
    ]

class Figure(Feature):
    def __init__(self):
        super(Figure, self).__init__()
        self._name = 'Figure'
        self.header = Feature()
        self.body   = Feature()
        self.script = Feature()
        #self.axes = []

        self.header._parent = self
        self.body._parent = self
        self.script._parent = self

        self._template = Template(u"""
        <!DOCTYPE html>
        <head>
            {{this.header.render(**kwargs)}}
        </head>
        <body>
            {{this.body.render(**kwargs)}}
        </body>
        <script>
            {{this.script.render(**kwargs)}}
        </script>
        """)

        # Create the meta tag
        self.header.add_children(Feature(
            '<meta http-equiv="content-type" content="text/html; charset=UTF-8" />'),
                                  name='meta_http')

        # Import Javascripts
        for name, url in _default_js:
            self.header.add_children(JavascriptLink(url), name=name)

        # Import Css
        for name, url in _default_css:
            self.header.add_children(CssLink(url), name=name)

        self.header.add_children(Feature("""
            <style>

            html, body {
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                }

            #map {
                position:absolute;
                top:0;
                bottom:0;
                right:0;
                left:0;
                }
            </style>
            """), name='css_style')

    def to_dict(self, depth=-1, **kwargs):
        out = super(Figure, self).to_dict(depth=depth, **kwargs)
        out['header'] = self.header.to_dict(depth=depth-1, **kwargs)
        out['body'] = self.body.to_dict(depth=depth-1, **kwargs)
        out['script'] = self.script.to_dict(depth=depth-1, **kwargs)
        return out

    def render(self, **kwargs):
        """TODO : docstring here."""
        for name, child in self._children.items():
            child.render(**kwargs)
        return self._template.render(this=self, kwargs=kwargs)

    def _repr_html_(self, figsize=(17,10), **kwargs):
        """Displays the Figure in a Jupyter notebook.

        Parameters
        ----------
            self : folium.Map object
                The map you want to display

            figsize : tuple of length 2, default (17,10)
                The size of the output you expect in inches.
                Output is 60dpi so that the output has same size as a
                matplotlib figure with the same figsize.

        """
        html = self.render(**kwargs)

        width, height = figsize

        iframe = '<iframe src="{html}" width="{width}px" height="{height}px"></iframe>'\
            .format(\
                    html = "data:text/html;base64,"+html.encode('utf8').encode('base64'),
                    #html = self.HTML.replace('"','&quot;'),
                    width = int(60.*width),
                    height= int(60.*height),
                   )
        return iframe

class Link(Feature):
    def get_code(self):
        if self.code is None:
            self.code = urlopen(self.url).read()
        return self.code
    def to_dict(self, depth=-1, **kwargs):
        out = super(Link, self).to_dict(depth=-1, **kwargs)
        out['url'] = self.url
        return out

class JavascriptLink(Link):
    def __init__(self, url, download=False):
        """Create a JavascriptLink object based on a url.
        Parameters
        ----------
            url : str
                The url to be linked
            download : bool, default False
                Whether the target document shall be loaded right now.
        """
        super(JavascriptLink, self).__init__()
        self._name = 'JavascriptLink'
        self.url = url
        self.code = None
        if download:
            self.get_code()

        self._template = Template(u"""
        {% if kwargs.get("embedded",False) %}
            <script>{{this.get_code()}}</script>
        {% else %}
            <script src="{{this.url}}"></script>
        {% endif %}
        """)

class CssLink(Link):
    def __init__(self, url, download=False):
        """Create a CssLink object based on a url.
        Parameters
        ----------
            url : str
                The url to be linked
            download : bool, default False
                Whether the target document shall be loaded right now.
        """
        super(CssLink, self).__init__()
        self._name = 'CssLink'
        self.url = url
        self.code = None
        if download:
            self.get_code()

        self._template = Template(u"""
        {% if kwargs.get("embedded",False) %}
            <style>{{this.get_code()}}</style>
        {% else %}
            <link rel="stylesheet" href="{{this.url}}" />
        {% endif %}
        """)

def _parse_size(value):
    try:
        if isinstance(value, int):
            value_type = 'px'
            assert value > 0
        else:
            value_type = '%'
            value = int(value.strip('%'))
            assert 0 <= value <= 100
    except:
        msg = "Cannot parse value {!r} as {!r}".format
        raise ValueError(msg(value, value_type))
    return value, value_type

class Map(Feature):
    def __init__(self, location=None, width='100%', height='100%',
                 tiles='OpenStreetMap', API_key=None, max_zoom=18, min_zoom=1,
                 zoom_start=10, attr=None, min_lat=-90, max_lat=90,
                 min_lon=-180, max_lon=180):
        """Create a Map with Folium and Leaflet.js

        Generate a base map of given width and height with either default
        tilesets or a custom tileset URL. The following tilesets are built-in
        to Folium. Pass any of the following to the "tiles" keyword:
            - "OpenStreetMap"
            - "MapQuest Open"
            - "MapQuest Open Aerial"
            - "Mapbox Bright" (Limited levels of zoom for free tiles)
            - "Mapbox Control Room" (Limited levels of zoom for free tiles)
            - "Stamen" (Terrain, Toner, and Watercolor)
            - "Cloudmade" (Must pass API key)
            - "Mapbox" (Must pass API key)
            - "CartoDB" (positron and dark_matter)
        You can pass a custom tileset to Folium by passing a Leaflet-style
        URL to the tiles parameter:
        http://{s}.yourtiles.com/{z}/{x}/{y}.png

        Parameters
        ----------
        location: tuple or list, default None
            Latitude and Longitude of Map (Northing, Easting).
        width: pixel int or percentage string (default: '100%')
            Width of the map.
        height: pixel int or percentage string (default: '100%')
            Height of the map.
        tiles: str, default 'OpenStreetMap'
            Map tileset to use. Can use defaults or pass a custom URL.
        API_key: str, default None
            API key for Cloudmade or Mapbox tiles.
        max_zoom: int, default 18
            Maximum zoom depth for the map.
        zoom_start: int, default 10
            Initial zoom level for the map.
        attr: string, default None
            Map tile attribution; only required if passing custom tile URL.

        Returns
        -------
        Folium Map Object

        Examples
        --------
        >>>map = folium.Map(location=[45.523, -122.675], width=750, height=500)
        >>>map = folium.Map(location=[45.523, -122.675],
                            tiles='Mapbox Control Room')
        >>>map = folium.Map(location=(45.523, -122.675), max_zoom=20,
                            tiles='Cloudmade', API_key='YourKey')
        >>>map = folium.Map(location=[45.523, -122.675], zoom_start=2,
                            tiles=('http://{s}.tiles.mapbox.com/v3/'
                                    'mapbox.control-room/{z}/{x}/{y}.png'),
                            attr='Mapbox attribution')

        """
        super(Map, self).__init__()
        self._name = 'Map'

        if not location:
            # If location is not passed, we center the map at 0,0 and ignore zoom
            self.location = [0, 0]
            self.zoom_start = min_zoom
        else:
            self.location = location
            self.zoom_start = zoom_start

        # Map Size Parameters.
        self.width  = _parse_size(width)
        self.height = _parse_size(height)

        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lon = min_lon
        self.max_lon = max_lon

        self.add_tile_layer(tiles=tiles, min_zoom=min_zoom, max_zoom=max_zoom,
                            attr=attr, API_key=API_key)

        self._template = Template(u"""
        {% macro body(this, kwargs) %}
            <div class="folium-map" id="map_{{this._id}}"
                style="width: {{this.width[0]}}{{this.width[1]}}; height: {{this.height[0]}}{{this.height[1]}}"></div>
        {% endmacro %}

        {% macro script(this, kwargs) %}

            var southWest = L.latLng({{ this.min_lat }}, {{ this.min_lon }});
            var northEast = L.latLng({{ this.max_lat }}, {{ this.max_lon }});
            var bounds = L.latLngBounds(southWest, northEast);

            var map_{{this._id}} = L.map('map_{{this._id}}', {
                                           center:[{{this.location[0]}},{{this.location[1]}}],
                                           zoom: {{this.zoom_start}},
                                           maxBounds: bounds,
                                           layers: []
                                         });
        {% endmacro %}
        """)

    def render(self, **kwargs):
        figure = self.get_root()

        body = self._template.module.__dict__.get('body',None)
        assert body is not None
        figure.body.add_children(Feature(body(self, kwargs)), name='map_'+self._id)

        script = self._template.module.__dict__.get('script',None)
        assert script is not None
        figure.script.add_children(Feature(script(self, kwargs)), name='map_'+self._id)

        for name, feature in self._children.items():
            feature.render(**kwargs)

    def _repr_html_(self, figsize=(17,10), **kwargs):
        """Displays the Map in a Jupyter notebook.

        Parameters
        ----------
            self : folium.Map object
                The map you want to display

            figsize : tuple of length 2, default (17,10)
                The size of the output you expect in inches.
                Output is 60dpi so that the output has same size as a
                matplotlib figure with the same figsize.

        """
        if self._parent is None:
            self.add_to(Figure())
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
            self._parent = None
        else:
            out = self._parent._repr_html_(figsize=figsize, **kwargs)
        return out

    def add_tile_layer(self, tiles='OpenStreetMap', name=None,
                       API_key=None, max_zoom=18, min_zoom=1,
                       attr=None, tile_name=None, tile_url=None,
                       active=False, **kwargs):
        if tile_name is not None:
            name = tile_name
            warnings.warn("'tile_name' is deprecated. Please use 'name' instead.")
        if tile_url is not None:
            tiles = tile_url
            warnings.warn("'tile_url' is deprecated. Please use 'tiles' instead.")

        tile_layer = TileLayer(tiles=tiles, name=name,
                               min_zoom=min_zoom, max_zoom=max_zoom,
                               attr=attr, API_key=API_key)
        self.add_children(tile_layer, name=tile_layer.tile_name)

class TileLayer(Feature):
    def __init__(self, tiles='OpenStreetMap', name=None,
                 min_zoom=1, max_zoom=18, attr=None, API_key=None):
        """TODO docstring here
        Parameters
        ----------
        """
        super(TileLayer, self).__init__()
        self._name = 'TileLayer'
        self.tile_name = name if name is not None else ''.join(tiles.lower().strip().split())

        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

        self.tiles = ''.join(tiles.lower().strip().split())
        if self.tiles in ('cloudmade', 'mapbox') and not API_key:
            raise ValueError('You must pass an API key if using Cloudmade'
                             ' or non-default Mapbox tiles.')
        templates = list(self._env.list_templates(filter_func=lambda x: x.startswith('tiles/')))
        tile_template = 'tiles/'+self.tiles+'/tiles.txt'
        attr_template = 'tiles/'+self.tiles+'/attr.txt'

        if tile_template in templates and attr_template in templates:
            self.tiles = self._env.get_template(tile_template).render(API_key=API_key)
            self.attr  = self._env.get_template(attr_template).render()
        else:
            self.tiles = tiles
            if not attr:
                raise ValueError('Custom tiles must'
                                 ' also be passed an attribution')
            self.attr = attr

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var tile_layer_{{this._id}} = L.tileLayer(
                '{{this.tiles}}',
                {
                    maxZoom: {{this.max_zoom}},
                    minZoom: {{this.min_zoom}},
                    attribution: '{{this.attr}}'
                    }
                ).addTo(map_{{this._parent._id}});

        {% endmacro %}
        """)

    def render(self, **kwargs):
        assert self._parent is not None, "You cannot render this Feature if it's not in a Map"
        for name, feature in self._children.items():
            feature.render(**kwargs)

        figure = self.get_root()

        script = self._template.module.__dict__.get('script',None)
        assert script is not None
        figure.script.add_children(Feature(script(self, kwargs)), name='tile_layer_'+self._id)

class WmsTileLayer(TileLayer):
    def __init__(self, url, name=None,
                 format=None, layers=None, transparent=True,
                attribution=None):
        """TODO docstring here
        Parameters
        ----------
        """
        super(TileLayer, self).__init__()
        self._name = 'WmsTileLayer'
        self.tile_name = name if name is not None else 'WmsTileLayer_'+self._id
        self.url = url
        self.format = format
        self.layers = layers
        self.transparent = transparent
        #if attribution is None:
        #    raise ValueError('WMS must'
        #                     ' also be passed an attribution')
        self.attribution = attribution

        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            var wms_tile_layer_{{this._id}} = L.tileLayer.wms(
                '{{ this.url }}',
                {
                    format:'{{ this.format }}',
                    transparent: {{ this.transparent.__str__().lower() }},
                    layers:'{{ this.layers }}',
                    attribution:'{{this.attribution}}'
                    }
                ).addTo(map_{{this._parent._id}});

        {% endmacro %}
        """)
