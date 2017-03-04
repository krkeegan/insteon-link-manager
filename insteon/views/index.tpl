<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Insteon Link Manager</title>

    <!-- Bootstrap -->
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css" integrity="sha384-BVYiiSIFeK1dGmJRAkycuHAHRg32OmUcww7on3RYdg4Va+PmSTsz/K68vbdEjh4u" crossorigin="anonymous">
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap-theme.min.css" integrity="sha384-rHyoN1iRsVXV4nD0JutlnGaslCJuC7uwjduW9SVrLvRYooPp2bWYgmgJQIXwl/Sp" crossorigin="anonymous">

    <!-- HTML5 shim and Respond.js for IE8 support of HTML5 elements and media queries -->
    <!-- WARNING: Respond.js doesn't work if you view the page via file:// -->
    <!--[if lt IE 9]>
      <script src="https://oss.maxcdn.com/html5shiv/3.7.3/html5shiv.min.js"></script>
      <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
    <![endif]-->
  </head>
  <body>
    <h3>Insteon Manager</h3>

    <div class="row">
      <div class="col-sm-4">
        <h4>Configure</h4>
        <a class="btn btn-default btn-block" href="#" role="button">Set Password</a>
        <a class="btn btn-default btn-block" href="#" role="button">Set Thread Count</a>
        <a class="btn btn-default btn-block" href="#" role="button">Restart</a>
        <a class="btn btn-default btn-block" href="#" role="button">Help</a>
      </div>
      <div class="col-sm-4">
        <h4>Modems</h4>
        % for modem in modems:
          % for key, value in modem.items():
            <a href='/modem/{{key}}'><!--Add Modem Name--> - {{key}}</a>
          % end
        % end
        <h4>Add Modem </h4>
        <a class="btn btn-default btn-block" href="#" role="button">Add a Hub</a>
        <a class="btn btn-default btn-block" href="#" role="button">Add a PLM</a>
      </div>
      <div class="col-sm-4 text-nowrap">
        <h4>Log <small> - <a href="#">Advanced Log</a></small></h4>
        18:28:33.12 - Lorem ipsum dolor sit amet, consectetur adipisicing elit,</br>
        18:28:32.11 - sed do eiusmod tempor incididunt ut labore et dolore </br>
        18:27:05.23 - magna aliqua. Ut enim ad minim veniam, quis nostrud </br>
        18:25:02.11 - exercitation ullamco laboris nisi ut aliquip ex ea commodo</br>
        18:22:54.45 - consequat. Duis aute irure dolor in reprehenderit in </br>
        18:21:45.12 - voluptate velit esse cillum dolore eu fugiat nulla </br>
        18:20:40.09 - pariatur. Excepteur sint occaecat cupidatat non proident</br>
        18:15:23.59 - sunt in culpa qui officia deserunt mollit anim id est</br>
      </div>
    </div>



    <!-- jQuery (necessary for Bootstrap's JavaScript plugins) -->
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.12.4/jquery.min.js"></script>
    <!-- Include all compiled plugins (below), or include individual files as needed -->
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" integrity="sha384-Tc5IQib027qvyjSMfHjOMaLkfuWVxZxUPnCJA7l2mCWNIpG9mGCD8wGNIcPD7Txa" crossorigin="anonymous"></script>
  </body>
</html>
