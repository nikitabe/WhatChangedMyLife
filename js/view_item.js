function HideEdit()
{
    $("#edit").fadeOut('slow', 
                       function(){ 
                        $("#view").fadeIn( 'slow' );
                       } );
}

$(document).ready( function(){
    $("#edit_button").click( function(){
        $("#view").fadeOut('slow', 
            function(){ 
                $("#edit").fadeIn( 'slow' );
            } );
    });


    $("#submit_edit").click( HideEdit );
    $("#cancel_edit").click( HideEdit );
                                        

                  
})
