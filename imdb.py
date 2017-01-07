from lxml import html
import requests
import re
import os

# Useful constants
IMDB_SEARCH_URL='http://www.imdb.com/find?ref_=nv_sr_fn&q='
IMDB_ACTOR_PAGE_PREFIX='http://www.imdb.com/name/'
IMDB_MOVIE_PAGE_PREFIX='http://www.imdb.com/title/'
HEADERS={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

# A class to represent our local movie database
class MDb:
    def __init__(self):
        # Map imdb IDs to movie names
        self.movieRegistry = {}
        self.actorRegistry = {}

        # Map actor IDs to lists of movie IDs
        self.filmographyLookup = {}

        # Map movie IDs to lists of actor IDs
        self.castLookup = {}


    def searchActor(self, name, verbose=False):
        # Get search results
        if verbose:
            print( 'Searching for actor \"{}\"...'.format(name) )
        query = name.strip().replace(' ', '+')
        searchResponse = requests.get( IMDB_SEARCH_URL + query, headers=HEADERS )
        searchPage = html.fromstring( searchResponse.content )

        # Find the IMDb resource ID of the first actor listed
        xpathToActorURL="//a[@name='nm']/../..//td[@class='result_text'][1]/a/@href"
        actorURL = searchPage.xpath( xpathToActorURL )[0]
        actorID = re.match(r'/name/(.+)/\?', actorURL).group(1)

        if verbose:
            print('\"{}\" actor ID found: {}'.format(name, actorID))

        return actorID

    def searchMovie(self, title, verbose=False):
        # Get search results
        if verbose:
            print( 'Searching for movie \"{}\"...'.format(title) )
        query = title.strip().replace(' ', '+')
        searchResponse = requests.get( IMDB_SEARCH_URL + query, headers=HEADERS )
        searchPage = html.fromstring( searchResponse.content )

        # Find the IMDb resource ID of the first movie listed
        xpathToMovieURL="//a[@name='tt']/../..//td[@class='result_text'][1]/a/@href"
        movieURL = searchPage.xpath( xpathToMovieURL )[0]
        movieID = re.match(r'/title/(.+)/\?', movieURL).group(1)

        if verbose:
            print('\"{}\" movie ID found: {}'.format(title, movieID))

        return movieID


    def loadActorFromID(self, actorID, verbose=False):
        # Load the actors page
        if verbose:
            print('Loading actor page for actor ID "{}"...'.format(actorID))
        ACTOR_PAGE_URL = IMDB_ACTOR_PAGE_PREFIX + actorID
        response = requests.get(ACTOR_PAGE_URL, headers=HEADERS)
        actorPage = html.fromstring( response.content )

        # Pull the actors name off the page
        xpathToName = '//span[@class="itemprop" and @itemprop="name"]'
        name = actorPage.xpath( xpathToName )[0].text
        if verbose:
            print('Actor ID "{}" name: "{}"'.format(actorID, name))

        # Pull all movie an movie IDs off page
        xpathToMovies = '//div[@class="filmo-category-section"][1]/div/b/a'
        movieElements = actorPage.xpath( xpathToMovies )

        # Record title and resource ID from each movie
        if verbose:
            print('Adding filmography of "{}" to movie registry...'.format(name))
        self.filmographyLookup[actorID] = []
        for element in movieElements:
            movieURL = element.get('href')
            movieID = re.match(r'/title/(.+)/', movieURL).group(1)
            title = element.text
            self.movieRegistry[movieID] = title
            self.filmographyLookup[actorID].append( movieID )



    def loadMovieFromID(self, movieID, verbose=False):
        # Load the movie page
        if verbose:
            print('Loading movie page for movie ID "{}"...'.format(movieID))
        MOVIE_PAGE_URL = IMDB_MOVIE_PAGE_PREFIX + movieID
        response = requests.get(MOVIE_PAGE_URL, headers=HEADERS)
        moviePage = html.fromstring( response.content )

        # Pull the movie title off the page
        xpathToTitle1 = '//*[@id="overview-top"]/h1/span[1]'
        xpathToTitle2 = '//div[@class="title_wrapper"]/h1/span[1]'
        elements = moviePage.xpath( xpathToTitle1 )
        if len(elements) == 0:
            elements = moviePage.xpath( xpathToTitle2 )
        if elements[0].text == '(':
            print('backing...')
            elements = elements[0].xpath('../..//h1')
        title = elements[0].text
        if verbose:
            print( 'Movie ID "{}" title: "{}"'.format(movieID, title) )

        # Load the cast page for this movie page
        if verbose:
            print('Loading cast page for movie ID "{}"...'.format(movieID))
        CAST_PAGE_URL = IMDB_MOVIE_PAGE_PREFIX + movieID + '/fullcredits'
        response = requests.get(CAST_PAGE_URL, headers=HEADERS)
        castPage = html.fromstring( response.content )

        # Pull the full cast off the page
        xpathToCast = '//table[@class="cast_list"]//td[@itemprop="actor"]'
        elements = castPage.xpath( xpathToCast )
        self.castLookup[movieID] = []
        for element in elements:
            actorURL = element.xpath("a")[0].get('href')
            actorID = re.match(r'/name/(.+)/', actorURL).group(1)
            actorName = element.xpath('a/span')[0].text
            self.castLookup[movieID].append( actorID )
            self.actorRegistry[actorID] = actorName

    def expandMovies(self, verbose=False):
        for movieID in self.movieRegistry:
            try:
                self.loadMovieFromID( movieID, verbose=verbose )
            except Exception:
                if verbose:
                    title = self.movieRegistry[movieID]
                    print('Error loading movie "{}". Skipping...'.format(title))

    def expandActors(self, verbose=False):
        for actorID in self.actorRegistry:
            try:
                self.loadActorFromID( actorID, verbose=verbose )
            except Exception:
                if verbose:
                    name = self.actorRegistry[actorID]
                    print('Error loading actor "{}". Skipping...'.format(name))

    def getCoactors(self, actorID, verbose=False):
        coactors = []
        for movieID in mdb.filmographyLookup[actorID]:
            try:
                for coactorID in mdb.castLookup[movieID]:
                    if coactorID not in coactors:
                        coactors.append(coactorID)
            except KeyError:
                if verbose:
                    title = self.movieRegistry[movieID]
                    print('Movie "{}" has no cast listed. Skipping...'.format(title))

        return coactors

if __name__ == '__main__':
    import pickle

    # Create a movie database object
    mdb = MDb()
    fassbenderID = mdb.searchActor('Michael Fasbender', verbose=True)
    downeyID = mdb.searchActor('Robert Downey Jr', verbose=True)

    # Populate the Movie Database object
    if not os.path.exists('save.mdb'):
        # If there is no save file download from IMDb
        mdb.loadActorFromID(fassbenderID, verbose=True)
        mdb.loadActorFromID(downeyID, verbose=True)
        mdb.expandMovies(verbose=True)

        # Save progress
        pickleBytes = pickle.dumps(mdb)
        with open('save.mdb', 'wb') as f:
            f.write(pickleBytes)
    else:
        # If there is a save file, load it
        print('Loading Movie Database from file...')
        with open('save.mdb', 'rb') as f:
            mdb = pickle.load(f)

    fassbenderCoactors = mdb.getCoactors( fassbenderID )
    downeyCoactors     = mdb.getCoactors( downeyID     )
    for actorID in fassbenderCoactors:
        if actorID in downeyCoactors:
            print(mdb.actorRegistry[actorID])
