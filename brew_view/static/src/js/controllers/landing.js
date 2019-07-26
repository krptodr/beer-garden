
landingController.$inject = [
  '$scope',
  '$rootScope',
  '$state',
  'SystemService',
  'UtilityService',
];

/**
 * landingController - Controller for the landing page.
 * @param  {Object} $scope         Angular's $scope object.
 * @param  {Object} $rootScope     Angular's $rootScope object.
 * @param  {Object} $state         Angular's $state object.
 * @param  {Object} SystemService  Beer-Garden's sytem service.
 * @param  {Object} UtilityService Beer-Garden's utility service.
 */
export default function landingController(
    $scope,
    $rootScope,
    $state,
    UtilityService) {
  $scope.setWindowTitle();

  $scope.util = UtilityService;

  $scope.successCallback = function(response) {
    $scope.response = response;
    $scope.data = response.data;
  };

  $scope.failureCallback = function(response) {
    $scope.response = response;
    $scope.data = {};
  };

  $scope.exploreSystem = function(system) {
    $state.go('namespace.system',
      {
        'name': system.name,
        'version': system.version,
      }
    );
  };

  $scope.response = $rootScope.sysResponse;
  $scope.data = $rootScope.systems;
};
