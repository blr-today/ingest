require 'net/http'
require 'sanitize'
require 'uri'
require 'set'
require 'date'

SANITIZE_CONFIG = {
  elements: %w[a span p i br],

  attributes: {
    'a' => %w[href title]
  },

  protocols: {
    'a' => { 'href' => %w[http https] }
  }
}.freeze

class LumaEvents < Jekyll::Generator
  safe true
  priority :highest
  MAX_EVENTS = 100

  def mock_request
    File.read '_development/fixture.json'
  end

  def parse_events(items)
    items
      .select { |item| item['kind']=='customsearch#result' }
      .select { |item| item['pagemap'].key? "Event" }
      .map do |item|
        {
          'title' => item['title'],
          'link' => item['link'],
          'snippet' => item['snippet'],
          'event' => item['pagemap']['Event'],
          'metatags' => item['pagemap']['metatags']
        }
      end
  end

  def get_events
    body = if Jekyll.env == 'production'
             make_request
           else
             File.read '_development/fixture.json'
           end
    data = JSON.parse(body)['items']
    parse_events(data)
  end

  # TODO: Paginate to 5 pages
  def make_request
    uri = URI('https://customsearch.googleapis.com/customsearch/v1')
    params = {
      :cx => 'b1443f9b7cc2b44ee',
      :dateRestrict => 'm6',
      :exactTerms => 'Bangalore|Bengaluru',
      :excludeTerms => '"Past Event", inurl:https://lu.ma/u/',
      :filter => '1',
      :sort => 'date',
      :key => ENV['LUMA_CSE_KEY_ID'],
    }
    uri.query = URI.encode_www_form(params)

    req = Net::HTTP::Get.new(uri)
    req['Accept'] = 'application/json'

    req_options = {
      use_ssl: uri.scheme == 'https'
    }
    res = Net::HTTP.start(uri.hostname, uri.port, req_options) do |http|
      http.request(req)
    end
    res.body
  end

end
