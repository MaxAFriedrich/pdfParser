# pdfParser

This program converts one or multiple PDFs to easily readable plain text. Unlike other programs like [Poppler's pdftotext](https://en.wikipedia.org/wiki/Poppler_(software)#poppler-utils), it not only converts the PDF to plain text, but also improves readability by removing unnecessary new lines, spaces, headers, and footers.

## Quick start

NOTE: This program has been designed with python 3.10 and later in mind.

Download this repository:

``` bash
git clone https://github.com/MaxAFriedrich/pdfParser
cd pdfParser
```

Then run the program, providing files as arguments.

``` bash
python pdfParser.py /location/of/pdf/filename.pdf
```

It may be useful to alias this program so you can run it from other location in your environment.

## License

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.