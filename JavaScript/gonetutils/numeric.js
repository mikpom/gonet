module.exports = {getBinSizes : getBinSizes,
                  createBinThresholds : createBinThresholds};

function getBinSizes(N, bins=5) {
    var indexBins = [];
    for (var i = 0; i < bins; i++) {
        indexBins[i] = 0;
    }
    for (var i = 0; i < N; i++) {
        indexBins[i % bins] += 1;
    }
    return indexBins;
}

function createBinThresholds(ar, bins=5) {
    ar.sort(function(a, b){return a-b});
    var binSizes = getBinSizes(ar.length, bins);
    var indexes = [];
    binSizes.filter(function(s){return s != 0;}).forEach(function(s, i){
        if (i==0) {
            indexes[i] = binSizes[i] - 1;
        }
        else {
            indexes[i] = indexes[i-1] + binSizes[i];
        }
    });
    var thr = indexes.map(function(i) {return ar[i];});
    return thr;
}
