var gulp = require('gulp'),
    useref = require('gulp-useref'),
    gulpif = require('gulp-if'),
    replace = require('gulp-replace'),
    uglify = require('gulp-uglify'),
    cleanCss = require('gulp-clean-css'),
    flatten = require('gulp-flatten'),
    del = require('del');

gulp.task('deploy', function () {
    return gulp.src('g3w-admin/templates/base.html')
        .pipe(replace(/"{% static /g,''))
        .pipe(replace(/ %}"/g,''))
        .pipe(useref({ searchPath: [
            'g3w-admin/core/static',
        ] }))
        .pipe(gulpif('*.js', uglify()))
        .pipe(gulpif('*.css', cleanCss({
            root: 'g3w-admin/core/static/bower_components/icheck/skins',
            rebase: false
        })))
        .pipe(gulp.dest('g3w-admin/core/static/dist'));
});

gulp.task('icheck_png', function () {
  return gulp.src(['g3w-admin/core/static/bower_components/icheck/skins/flat/green*.png'])
    .pipe(flatten())
    .pipe(gulp.dest('g3w-admin/core/static/dist/css/'))
});

gulp.task('fonts', function () {
  return gulp.src(['g3w-admin/core/static/bower_components/**/*.{eot,ttf,woff,woff2}'])
    .pipe(flatten())
    .pipe(gulp.dest('g3w-admin/core/static/dist/fonts/'))
});

gulp.task('default', ['deploy', 'icheck_png', 'fonts'], function(){
    return del([
      'g3w-admin/core/static/dist/base.html'
    ]);
});