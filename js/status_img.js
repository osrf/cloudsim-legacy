function status_img( color)
{
	var str = "";
    if(color == "blue")
        str = "<img width='18' src='/js/images/blue_status.png'></img>";
    else if(color == "green")
        str = "<img width='18' src='/js/images/green_status.png'></img>";
    else if(color == "orange")
        str = "<img width='18' src='/js/images/orange_status.png'></img>";
    else if(color == "red")
        str = "<img width='18' src='/js/images/red_status.png'></img>";
    else if(color == "yellow")
        str = "<img width='18' src='/js/images/yellow_status.png'></img>";
    else if(color == "gray")
        str = "<img width='18' src='/js/images/gray_status.png'></img>";
    return str;
    
    
    
}