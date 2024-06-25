import lxml.etree

def fetch_bookmyshow():
	# read out/movie-shows.xml
	with open("out/movie-shows.xml", "r") as f:
		tree = lxml.etree.fromstring(f.read())
		for url in tree.xpath("//*[contains(text(), '-bengaluru/movie-bang-')]"):
			print(url.text)

if __name__ == "__main__":
	fetch_bookmyshow()
