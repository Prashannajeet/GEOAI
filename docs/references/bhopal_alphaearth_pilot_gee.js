// Bhopal AlphaEarth Change Intelligence Pilot
// Run in the Google Earth Engine Code Editor: https://code.earthengine.google.com/
//
// Dataset attribution required by Google:
// "The AlphaEarth Foundations Satellite Embedding dataset is produced by Google and Google DeepMind."

var cityName = 'Bhopal, Madhya Pradesh, India';
var center = ee.Geometry.Point([77.4126, 23.2599]);
var aoi = center.buffer(25000).bounds(); // 25 km city pilot area; adjust as needed.

var startYear = 2017;
var endYear = 2024;
var changeThreshold = 0.18; // Raise for fewer hotspots, lower for more.
var minPatchPixels = 25; // 25 pixels at 10 m ~= 0.25 ha.

var bands = ee.List.sequence(0, 63).map(function(i) {
  return ee.String('A').cat(ee.Number(i).format('%02d'));
});

var embeddings = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL');

function annualEmbedding(year) {
  var start = ee.Date.fromYMD(year, 1, 1);
  var end = start.advance(1, 'year');
  return embeddings
    .filterDate(start, end)
    .filterBounds(aoi)
    .mosaic()
    .select(bands)
    .clip(aoi);
}

var imageStart = annualEmbedding(startYear);
var imageEnd = annualEmbedding(endYear);

// Embeddings are unit-length, so dot product is cosine similarity.
// Higher changeScore means lower similarity between years.
var similarity = imageStart.multiply(imageEnd).reduce(ee.Reducer.sum()).rename('similarity');
var changeScore = ee.Image(1).subtract(similarity).rename('change_score').clip(aoi);

// Hotspot mask with a simple connected-pixel size filter.
var rawHotspots = changeScore.gt(changeThreshold).selfMask();
var connected = rawHotspots.connectedPixelCount(100, true);
var hotspots = rawHotspots.updateMask(connected.gte(minPatchPixels)).rename('hotspot');

// Convert hotspots to polygons and rank them by mean change score and area.
var vectors = hotspots.reduceToVectors({
  geometry: aoi,
  scale: 10,
  geometryType: 'polygon',
  eightConnected: true,
  labelProperty: 'hotspot',
  reducer: ee.Reducer.countEvery(),
  maxPixels: 1e10,
  tileScale: 4
});

var rankedHotspots = vectors.map(function(feature) {
  var geom = feature.geometry();
  var stats = changeScore.reduceRegion({
    reducer: ee.Reducer.mean().combine({
      reducer2: ee.Reducer.max(),
      sharedInputs: true
    }),
    geometry: geom,
    scale: 10,
    maxPixels: 1e8,
    tileScale: 4
  });

  return feature.set({
    city: cityName,
    start_year: startYear,
    end_year: endYear,
    mean_change: stats.get('change_score_mean'),
    max_change: stats.get('change_score_max'),
    area_m2: geom.area(1),
    area_ha: geom.area(1).divide(10000),
    threshold: changeThreshold
  });
}).sort('mean_change', false);

// Map display.
Map.setOptions('SATELLITE');
Map.centerObject(center, 11);
Map.addLayer(aoi, {color: 'cyan'}, 'Bhopal pilot AOI', false);
Map.addLayer(
  imageStart,
  {min: -0.3, max: 0.3, bands: ['A01', 'A16', 'A09']},
  startYear + ' AlphaEarth embeddings',
  false
);
Map.addLayer(
  imageEnd,
  {min: -0.3, max: 0.3, bands: ['A01', 'A16', 'A09']},
  endYear + ' AlphaEarth embeddings',
  false
);
Map.addLayer(
  similarity,
  {min: 0.75, max: 1, palette: ['red', 'yellow', 'black']},
  'Similarity, ' + startYear + '-' + endYear,
  false
);
Map.addLayer(
  changeScore,
  {min: 0, max: 0.3, palette: ['white', 'yellow', 'orange', 'red', 'purple']},
  'Change score, ' + startYear + '-' + endYear
);
Map.addLayer(
  rankedHotspots.style({color: 'red', fillColor: '00000000', width: 2}),
  {},
  'Ranked change hotspots'
);

print('Pilot city', cityName);
print('AOI area km2', aoi.area(1).divide(1e6));
print('Top ranked hotspots', rankedHotspots.limit(50));

// Exports. Start these from the Tasks tab after running the script.
Export.table.toDrive({
  collection: rankedHotspots,
  description: 'bhopal_alphaearth_change_hotspots_' + startYear + '_' + endYear,
  fileNamePrefix: 'bhopal_alphaearth_change_hotspots_' + startYear + '_' + endYear,
  fileFormat: 'GeoJSON'
});

Export.image.toDrive({
  image: changeScore,
  description: 'bhopal_alphaearth_change_score_' + startYear + '_' + endYear,
  fileNamePrefix: 'bhopal_alphaearth_change_score_' + startYear + '_' + endYear,
  region: aoi,
  scale: 10,
  maxPixels: 1e10
});
