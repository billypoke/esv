// loads various gulp modules
var gulp = require('gulp');
var concat = require('gulp-concat');
var cleanCSS = require('gulp-clean-css');
var autoprefixer = require('gulp-autoprefixer');
var htmlmin = require('gulp-htmlmin');

// create task
gulp.task('css', function(){
    return gulp.src([
        'static/css/bootstrap.min.css',
        'static/css/bootstrap_xl.css',
        'static/css/sticky_footer.css',
        'static/css/custom.css'
    ])
        .pipe(cleanCSS())
        .pipe(autoprefixer('last 2 version', 'safari 5', 'ie 8', 'ie 9'))
        .pipe(concat('style.min.css'))
        .pipe(gulp.dest('static/css'));
});

gulp.task('minify', function() {
  return gulp.src([
      'templates/misc/*.html',
      'templates/ships/*.html',
      'templates/weapons/*.html',
      'templates/tank/*.html',
      'templates/*.html'
  ])
    .pipe(htmlmin({
        collapseWhitespace: true,
        removeComments: true
    }))
    .pipe(gulp.dest('templates/dist'));
});