# graduateproject

Description:

Image processing is used for detecting human chess move. Python with
OpenCV (Open Source Computer Vision Library) interface is a good option to make it easier.
Before human movement, camera takes a picture. After that, RGB image is converted to
grayscale. After using the Gaussian Thresholding method, Canny Edge Detection is applied.
The biggest contour of the image is assumed to be chessboard. After finding the corner of the
chessboard, 4 point transform is applied. If there is a chess piece in one of the chess squares,
the white pixel value is much higher than the value of square with no chess pieces. After this
operation, the image is converted to an 8x8 array as shown in Figures 3.b and 3.d. Value of
elements of an array depends on whether there is a piece or not. If there is a piece it takes 1.
Otherwise, it takes 0. To detect a chess move, the element that turns from 0 to 1 or from 1 to 0.
Blue parts of the Figure 3.d represents the piece arrival square that’s value turned from 1 to 0.
Red one is departure square that’s value turned from 0 to 1.

Block Diagram:

 	Take Image 
	  	|
  		v 
 		Grayscale&Theresholding
  		|
  		v 
 	Edge Detection
  		|
 	 	v
 	Board Detection 
  		|
  		v 
 	Perspective Transformation
  		|
  		v 
 	Chess Piece Detection
  		|
  		v 
  	Chess Array

This process is repeated through the game. The image processing part is performed
before human chess move and after chess move. The result is given to the artificial intelligence
part. With the Sunfish artificial intelligence, robot’s next chess move is decided.