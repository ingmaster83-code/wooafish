require 'json'

module Jekyll
  class FishingPageGenerator < Generator
    safe true
    priority :normal

    TYPE_ORDER = %w[reservoir sea port island lighthouse coast flatland valley etc].freeze
    TYPE_LABELS = {
      "reservoir" => "저수지", "sea" => "바다", "port" => "항구/포구", "island" => "섬",
      "lighthouse" => "등대", "coast" => "해안절경", "flatland" => "하천/평지",
      "valley" => "계곡", "etc" => "기타(실내 등)"
    }.freeze
    TYPE_ICONS = {
      "reservoir" => "🏞️", "sea" => "🌊", "port" => "⚓", "island" => "🏝️",
      "lighthouse" => "🚨", "coast" => "🌊", "flatland" => "🌾",
      "valley" => "⛰️", "etc" => "🎣"
    }.freeze

    def generate(site)
      spots = site.data['fishing_spots']
      return unless spots&.any?

      Jekyll.logger.info "FishingGenerator:", "#{spots.size}개 낚시터 페이지 생성 중..."

      spots.each do |spot|
        same_region = spots
          .select { |s| s['region'] == spot['region'] && s['slug'] != spot['slug'] }
          .first(8)
          .map { |s| { 'slug' => s['slug'], 'name' => s['spotName'], 'city' => s['city'], 'typeLabel' => s['typeLabel'], 'typeIcon' => s['typeIcon'] } }

        same_type = spots
          .select { |s| s['typeSlug'] == spot['typeSlug'] && s['slug'] != spot['slug'] }
          .first(8)
          .map { |s| { 'slug' => s['slug'], 'name' => s['spotName'], 'region' => s['region'], 'city' => s['city'] } }

        species = spot['species'] || []
        same_species = species.empty? ? [] : spots
          .select { |s| s['slug'] != spot['slug'] && !((s['species'] || []) & species).empty? }
          .first(8)
          .map { |s| { 'slug' => s['slug'], 'name' => s['spotName'], 'region' => s['region'], 'city' => s['city'], 'sharedSpecies' => ((s['species'] || []) & species).first } }

        # 이전/다음: 같은 지역 내에서 시군구 -> 이름 순 정렬 후 순환
        region_ordered = spots
          .select { |s| s['region'] == spot['region'] }
          .sort_by { |s| [s['city'].to_s, s['spotName'].to_s] }
        idx = region_ordered.index { |s| s['slug'] == spot['slug'] }
        prev_spot = nil
        next_spot = nil
        if idx && region_ordered.size > 1
          p = region_ordered[(idx - 1) % region_ordered.size]
          n = region_ordered[(idx + 1) % region_ordered.size]
          prev_spot = { 'slug' => p['slug'], 'name' => p['spotName'] }
          next_spot = { 'slug' => n['slug'], 'name' => n['spotName'] }
        end

        site.pages << SpotPage.new(site, spot, same_region, same_type, same_species, prev_spot, next_spot)
      end

      by_region = spots.group_by { |s| s['region'] }
      by_region.each do |region, region_spots|
        slug = region_spots.first['regionSlug']
        site.pages << RegionPage.new(site, region, slug, region_spots)
      end

      by_type = spots.group_by { |s| s['typeSlug'] }
      by_type.each do |type_slug, type_spots|
        site.pages << TypePage.new(site, type_slug, type_spots)
      end

      site.pages << SearchIndexPage.new(site, spots)

      Jekyll.logger.info "FishingGenerator:", "완료 (#{spots.size}개 낚시터)"
    end
  end

  class SpotPage < Page
    def initialize(site, spot, same_region, same_type, same_species, prev_spot, next_spot)
      @site = site
      @base = site.source
      @dir  = "spot/#{spot['slug']}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'spot.html')
      self.data.merge!(spot)
      self.data['layout']       = 'spot'
      self.data['same_region']  = same_region
      self.data['same_type']    = same_type
      self.data['same_species'] = same_species
      self.data['prev_spot']    = prev_spot
      self.data['next_spot']    = next_spot

      species_str = (spot['species'] || []).join(', ')
      fee_str = spot['fee'].to_s.empty? ? '요금 정보 없음' : spot['fee']
      self.data['title'] = "#{spot['spotName']} 위치·이용요금·주요어종 | #{spot['region']} #{spot['city']} 낚시터"
      self.data['description'] = "#{spot['spotName']}(#{spot['region']} #{spot['city']}, #{spot['typeLabel']}) 낚시터 정보. " \
        "#{species_str.empty? ? '' : "주요어종: #{species_str}. "}이용요금: #{fee_str}."
    end
  end

  class RegionPage < Page
    def initialize(site, region, slug, spots)
      @site = site
      @base = site.source
      @dir  = "region/#{slug}"
      @name = 'index.html'

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'region.html')
      self.data['layout']      = 'region'
      self.data['region']      = region
      self.data['region_slug'] = slug
      self.data['spots']       = spots
      cities = spots.map { |s| s['city'] }.uniq.first(4).join(', ')
      self.data['title']       = "#{region} 낚시터 정보 총정리 | 전국 낚시터 #{spots.size}곳"
      self.data['description'] = "#{region} 낚시터 #{spots.size}곳 정보 총정리! #{cities} 등 지역별 낚시터 위치·주요어종·이용요금을 한눈에 확인하세요."
    end
  end

  class TypePage < Page
    def initialize(site, type_slug, spots)
      @site = site
      @base = site.source
      @dir  = "type/#{type_slug}"
      @name = 'index.html'

      label = FishingPageGenerator::TYPE_LABELS[type_slug] || type_slug

      self.process(@name)
      self.read_yaml(File.join(@base, '_layouts'), 'type.html')
      self.data['layout']     = 'type'
      self.data['type_slug']  = type_slug
      self.data['type_label'] = label
      self.data['type_icon']  = FishingPageGenerator::TYPE_ICONS[type_slug] || '🎣'
      self.data['spots']      = spots
      regions = spots.map { |s| s['region'] }.uniq.first(5).join(', ')
      self.data['title']       = "전국 #{label} 낚시터 목록 #{spots.size}곳"
      self.data['description'] = "전국 #{label} 낚시터 #{spots.size}곳 목록. #{regions} 등 지역별 #{label} 낚시터 정보를 확인하세요."
    end
  end

  class SearchIndexPage < Page
    def initialize(site, spots)
      @site = site
      @base = site.source
      @dir  = ''
      @name = 'search_index.json'

      self.process(@name)
      self.data = { 'layout' => nil, 'sitemap' => false }

      index = spots.map do |s|
        {
          'slug' => s['slug'], 'name' => s['spotName'], 'region' => s['region'], 'city' => s['city'],
          'typeLabel' => s['typeLabel'], 'species' => s['species'], 'address' => s['address'],
        }
      end

      self.content = index.to_json
    end

    def output   = self.content
    def render(layouts, registers); end
  end
end
