const path = require('path');
const webpack = require('webpack');
var parseArgs = require('minimist');
const MinifyPlugin = require('babel-minify-webpack-plugin');

new webpack.ProvidePlugin({
  $: 'jquery',
  jQuery: 'jquery'
});

var webpackArgs = parseArgs(process.argv.slice(2), {default:{mode:"development"}});

var conf = [
    {
        entry: './result_page.js',
        output: {
            path: path.resolve(__dirname, '../static/JavaScript/bundles'),
            filename: 'GOnet_result_page.bundle.js'
        },
        resolve: {modules:["node_modules", path.resolve(__dirname), path.resolve(__dirname, 'node_modules')]},
        module: {
            rules: [
                {
                    test: /\.(png|svg|jpg|gif)$/,
                    loader: 'url-loader',
                            options: {
                                // Images larger than 10 KB won’t be inlined
                                limit: 10 * 1024
                            }
                }]
        }
    },
    {
        entry: './submit_page.js',
        output: {
            path: path.resolve(__dirname, '../static/JavaScript/bundles'),
            filename: 'GOnet_submit_page.bundle.js'
        },
    },
    {
        entry: './wait_page.js',
        output: {
            path: path.resolve(__dirname, '../static/JavaScript/bundles'),
            filename: 'GOnet_wait_page.bundle.js'
        },
    },
];

if (webpackArgs.mode=="development") {
    conf.forEach(function(c){
        c['devtool'] = 'inline-source-map';
        c['mode'] = "development";
    });
}
else if (webpackArgs.mode=="production") {
    conf.forEach(function(c){
        c['plugins'] = [
            new MinifyPlugin(minifyOpts={}, pluginOpts={})
        ];
        c['mode'] = 'production';
    });
}

module.exports = conf;
