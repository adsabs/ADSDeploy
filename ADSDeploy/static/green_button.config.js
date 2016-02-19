define([], function() {
  var config = {

    targetElement: 'div#green-button-app',
    TargetWidget: 'js/widgets/green_button/widget',
    apiRoot: '//' + document.location.host + '/' // change this if the api is not at the same place as the webpage

  };
  return config;
});
