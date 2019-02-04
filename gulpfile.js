// loads various gulp modules
let gulp = require('gulp');
let concat = require('gulp-concat');
let cleanCSS = require('gulp-clean-css');
let autoprefixer = require('gulp-autoprefixer');
let htmlmin = require('gulp-htmlmin');
let watch = require('gulp-watch');


gulp.task('css', function () {
    let cssFiles = [
        'static/css/bootstrap.min.css',
        'static/css/bootstrap_xl.css',
        'static/css/sticky_footer.css',
        'static/css/custom.css'
    ];
    return gulp.src(cssFiles)
        .pipe(cleanCSS())
        .pipe(autoprefixer('last 2 version', 'safari 5', 'ie 8', 'ie 9'))
        .pipe(concat('style.min.css'))
        .pipe(gulp.dest('static/css'));
});

gulp.task('csswatch', function () {
    let cssFiles = [
        'static/css/bootstrap.min.css',
        'static/css/bootstrap_xl.css',
        'static/css/sticky_footer.css',
        'static/css/custom.css'
    ];
    return gulp.src(cssFiles)
        .pipe(watch(cssFiles, {verbose: true}))
        .pipe(cleanCSS())
        .pipe(autoprefixer('last 2 version', 'safari 5', 'ie 8', 'ie 9'))
        .pipe(concat('style.min.css'))
        .pipe(gulp.dest('static/css'));
});

gulp.task('htmlminify', function () {
    let htmlFiles = [
        'templates/misc/*.html',
        'templates/ships/*.html',
        'templates/weapons/*.html',
        'templates/tank/*.html',
        'templates/*.html'
    ];
    return gulp.src(htmlFiles)
        .pipe(htmlmin({
            collapseWhitespace: true,
            removeComments: true
        }))
        .pipe(gulp.dest('templates/dist'));
});

gulp.task('htmlminifywatch', function () {
    let htmlFiles = [
        'templates/misc/*.html',
        'templates/ships/*.html',
        'templates/weapons/*.html',
        'templates/tank/*.html',
        'templates/*.html'
    ];
    return gulp.src(htmlFiles)
        .pipe(watch(htmlFiles, {verbose: true}))
        .pipe(htmlmin({
            collapseWhitespace: true,
            removeComments: true
        }))
        .pipe(gulp.dest('templates/dist'));
});
