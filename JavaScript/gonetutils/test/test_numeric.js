var chai = require('chai'),
    should = chai.should(),
    assert = chai.assert,
    numutils = require('../numeric'),
    cytoscape = require('cytoscape');



describe('Testing numutils', function() {
    it('should return correct bin sizes', function() {
        var binSizes = numutils.getBinSizes(107);
        assert.deepEqual(binSizes, [22, 22, 21, 21, 21]);
    });

    it('should return correct bin sizes (if num of bins greater)', function() {
        var binSizes = numutils.getBinSizes(4, 5);
        assert.deepEqual(binSizes, [1, 1, 1, 1, 0]);
    });

    it('should create correct bin threasholds', function() {
        var list = [];
        for (var i=1; i <= 107; i++) {
            list.push(i * 1e-5);
        }
        var thrs = numutils.createBinThresholds(list, 5);
        var binSizes = thrs.map(function(thr, i){
            if (i==0) {
                var binEntries = list.filter(function(e){return (e<=thr)});
            }
            else {
                var binEntries = list.filter(function(e){return ((e<=thr)&(e>thrs[i-1]))});
            }
            return binEntries.length;
        });
        assert.isAbove(thrs[thrs.length-1], thrs[0])
        assert.deepEqual(binSizes, [22, 22, 21, 21, 21]);
    });
    it('should split pvalues correctly', function() {
        var pvals = [0.0000472433, 0.0000202627, 0.0000623126, 0.000097354, 0.0000045596,
                     0.0000634061, 0.000019071600000000002, 0.0000144357, 0.0000374004,
                     8.578000000000001e-7, 0.0000654225, 0.0000410588, 0.0000316322,
                     0.0000089411, 0.0000023897, 0.000040704, 0.0000090083,
                     0.000045411600000000004, 0.000006987200000000001,
                     0.000014726900000000001, 0.0000162457];
        
        var expectedBinSizes = numutils.getBinSizes(pvals.length, 5);
        var thrs = numutils.createBinThresholds(pvals, 5);
        assert.isAbove(thrs[thrs.length-1], thrs[0]);
        var actualBinSizes = thrs.map(function(thr, i){
            var binEntries;
            if (i==0) {
                binEntries = pvals.filter(function(e){return (e<=thr)});
            }
            else {
                binEntries = pvals.filter(function(e){return ((e<=thr)&(e>thrs[i-1]))});
            }
            return binEntries.length;
        });
        assert.deepEqual(actualBinSizes, expectedBinSizes);
    });
    it("Return sorted array of elements if number of bins is greater", function() {
        var ar = [2,1,5,3];
        assert.sameOrderedMembers(numutils.createBinThresholds(ar, 5), [1,2,3,5]);
    });
    it("Return empty array if empty array is passed", function() {
        var ar = [];
        assert.equal(numutils.createBinThresholds(ar, 5).length, 0);
    });

});

