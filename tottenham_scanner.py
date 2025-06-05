import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import time
import json
import hashlib
from datetime import datetime
import os

def parse_rss_date(date_string):
    """Parse various RSS date formats"""
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    formats = [
        '%a, %d %b %Y %H:%M:%S %Z',      # Thu, 05 Jun 2025 11:14:56 GMT
        '%a, %d %b %Y %H:%M:%S %z',      # With timezone offset
        '%Y-%m-%dT%H:%M:%S%z',           # ISO format
        '%Y-%m-%d %H:%M:%S',             # Simple format
        '%d %b %Y %H:%M:%S',             # Without day name
        '%a, %d %b %Y %H:%M:%S',         # No timezone
        '%d %b %Y, %H:%M',               # Alternative format
        '%d %b %Y',                      # Date only
    ]
    
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_string, fmt)
            if parsed.tzinfo is not None:
                parsed = parsed.replace(tzinfo=None)
            return parsed
        except ValueError:
            continue
    
    return None

class TottenhamAIScanner:
    def __init__(self):
        self.primary_keywords = ['tottenham', 'spurs', 'thfc']
        self.cutoff_date = datetime(2025, 6, 1, 0, 0, 0)
        
        self.feeds = {
            'BBC Sport': {
                'url': 'http://feeds.bbci.co.uk/sport/football/rss.xml',
                'homepage': 'https://www.bbc.com/sport/football'
            },
            'Guardian Football': {
                'url': 'https://www.theguardian.com/football/rss',
                'homepage': 'https://www.theguardian.com/football'
            },
            'Sky Sports': {
                'url': 'https://www.skysports.com/rss/12040',
                'homepage': 'https://www.skysports.com/football'
            },
            'Mirror Football': {
                'url': 'https://www.mirror.co.uk/sport/football/rss.xml',
                'homepage': 'https://www.mirror.co.uk/sport/football'
            },
            'TeamTalk': {
                'url': 'https://www.teamtalk.com/feed',
                'homepage': 'https://www.teamtalk.com'
            },
            'Football365': {
                'url': 'https://www.football365.com/feed',
                'homepage': 'https://www.football365.com'
            },
            'Football Insider': {
                'url': 'https://www.footballinsider247.com/feed/',
                'homepage': 'https://www.footballinsider247.com'
            },
            'Tottenham Official': {
                'url': 'https://www.tottenhamhotspur.com/news/feed/',
                'homepage': 'https://www.tottenhamhotspur.com/news'
            },
            'TottenhamHotspurNews': {
                'url': 'https://www.tottenhamhotspurnews.com/feed/',
                'homepage': 'https://www.tottenhamhotspurnews.com'
            },
            'SpursWeb': {
                'url': 'https://www.spurs-web.com/feed/',
                'homepage': 'https://www.spurs-web.com'
            },
            'To The Lane And Back': {
                'url': 'https://tothelaneandback.com/feed/',
                'homepage': 'https://tothelaneandback.com'
            }
        }
        
        self.seen_articles_file = 'seen_articles.json'
        self.seen_articles = self.load_seen_articles()
        self.html_filename = 'index.html'
        self.is_initial_scan = not os.path.exists('articles_data.json')
    
    def is_article_after_cutoff(self, date_string):
        if not date_string:
            return True
        
        parsed_date = parse_rss_date(date_string)
        if parsed_date:
            if parsed_date.tzinfo is not None:
                parsed_date = parsed_date.replace(tzinfo=None)
            return parsed_date >= self.cutoff_date
        return True
        
    def load_seen_articles(self):
        if os.path.exists(self.seen_articles_file):
            try:
                with open(self.seen_articles_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_seen_articles(self):
        with open(self.seen_articles_file, 'w') as f:
            json.dump(self.seen_articles, f, indent=2)
    
    def get_article_id(self, url):
        return hashlib.md5(url.encode()).hexdigest()
    
    def parse_article_date(self, date_string):
        if not date_string:
            return None
        parsed_date = parse_rss_date(date_string)
        if parsed_date:
            return parsed_date.strftime('%d %B %Y, %H:%M')
        return date_string
    
    def extract_article_image(self, soup, url):
        try:
            image_selectors = [
                'meta[property="og:image"]',
                'meta[name="twitter:image"]',
                '.article-image img',
                '.featured-image img',
                '.post-thumbnail img',
                'article img:first-of-type'
            ]
            
            for selector in image_selectors:
                if 'meta' in selector:
                    element = soup.select_one(selector)
                    if element and element.get('content'):
                        img_url = element.get('content')
                        if self.is_valid_image_url(img_url):
                            return self.make_absolute_url(img_url, url)
                else:
                    element = soup.select_one(selector)
                    if element:
                        img_url = element.get('src') or element.get('data-src')
                        if img_url and self.is_valid_image_url(img_url):
                            return self.make_absolute_url(img_url, url)
            return None
        except:
            return None
    
    def is_valid_image_url(self, url):
        if not url:
            return False
        url_lower = url.lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        skip_patterns = ['placeholder', 'default', 'logo', 'avatar', 'icon']
        
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        return any(ext in url_lower for ext in image_extensions)
    
    def make_absolute_url(self, img_url, base_url):
        if img_url.startswith('http'):
            return img_url
        from urllib.parse import urljoin
        return urljoin(base_url, img_url)
    
    def is_primary_tottenham_story(self, title, description, full_content="", source_name=""):
        all_text = (title + " " + description + " " + full_content[:500]).lower()
        
        tottenham_sources = ['tottenhamhotspurnews', 'spurs-web', 'tothelaneandback', 'football.london']
        is_tottenham_source = any(source in source_name.lower() for source in tottenham_sources)
        
        if is_tottenham_source:
            return True
        
        primary_count = sum(all_text.count(keyword) for keyword in self.primary_keywords)
        if primary_count >= 1:
            return True
        
        return False
    
    def extract_full_article(self, url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            
            print('      🔍 Accessing: ' + url[:60] + '...')
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            image_url = self.extract_article_image(soup, url)
            
            for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                element.decompose()
            
            text_selectors = [
                '.entry-content p', '.article-body p', '.story-body p',
                '.content p', 'article p', 'main p'
            ]
            
            article_text = ""
            for selector in text_selectors:
                elements = soup.select(selector)
                if elements:
                    text_parts = [elem.get_text(strip=True) for elem in elements if len(elem.get_text(strip=True)) > 20]
                    if text_parts:
                        article_text = ' '.join(text_parts)
                        break
            
            if len(article_text) < 100:
                paragraphs = soup.find_all('p')
                text_parts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 15]
                article_text = ' '.join(text_parts)
            
            article_text = self.clean_text(article_text)
            print('      📄 ' + str(len(article_text)) + ' chars')
            if image_url:
                print('      🖼️  Image found')
            
            return article_text, image_url
            
        except Exception as e:
            print('      ⚠️  Error: ' + str(e))
            return "", None
    
    def clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def create_smart_summary(self, title, full_text, url):
        """Create a smart summary using keyword-based sentence selection"""
        if not full_text or len(full_text) < 200:
            return "Read the full article for complete details on this Tottenham story."
        
        clean_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Remove common website clutter
        cleanup_patterns = [
            r'READ MORE:.*?(?=\.|$)',
            r'CLICK HERE.*?(?=\.|$)',
            r'Sign up.*?(?=\.|$)',
            r'Subscribe.*?(?=\.|$)',
        ]
        
        for pattern in cleanup_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', clean_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30 and len(s.strip()) < 300]
        
        if not sentences:
            return "Read the full article for complete details on this Tottenham story."
        
        tottenham_keywords = ['tottenham', 'spurs', 'thfc', 'postecoglou', 'ange', 'levy', 'son', 'kane']
        action_words = ['sign', 'buy', 'sell', 'target', 'win', 'lose', 'beat', 'defeat', 'transfer']
        
        scored_sentences = []
        for i, sentence in enumerate(sentences[:15]):
            score = 0
            sentence_lower = sentence.lower()
            
            for keyword in tottenham_keywords:
                score += sentence_lower.count(keyword) * 5
            
            for word in action_words:
                if word in sentence_lower:
                    score += 3
            
            score += (15 - i) * 0.5
            
            if len(sentence) > 200:
                score -= 2
            
            if score > 0:
                scored_sentences.append((score, sentence, i))
        
        if not scored_sentences:
            return "Read the full article for complete details on this Tottenham story."
        
        scored_sentences.sort(key=lambda x: -x[0])
        
        summary_parts = []
        total_length = 0
        target_length = 380
        
        for score, sentence, position in scored_sentences:
            sentence_length = len(sentence)
            
            if total_length + sentence_length > target_length:
                if total_length < 200:
                    remaining_space = target_length - total_length
                    if remaining_space > 50:
                        truncated = sentence[:remaining_space].strip()
                        last_space = truncated.rfind(' ')
                        if last_space > remaining_space * 0.7:
                            truncated = truncated[:last_space] + '...'
                            summary_parts.append(truncated)
                            break
                else:
                    break
            else:
                summary_parts.append(sentence)
                total_length += sentence_length
                
                if total_length >= 250:
                    break
        
        if not summary_parts:
            for score, sentence, position in scored_sentences[:3]:
                if len(sentence) <= 400:
                    return sentence
            return "Read the full article for complete details on this Tottenham story."
        
        summary = ' '.join(summary_parts)
        summary = re.sub(r'\s+', ' ', summary).strip()
        
        if summary and not summary.endswith(('.', '!', '?', '...')):
            summary += '.'
        
        return summary if len(summary) > 50 else "Read the full article for complete details on this Tottenham story."
    
    def check_for_articles(self):
        new_articles = []
        items_to_check = 25 if self.is_initial_scan else 15
        
        for source_name, source_info in self.feeds.items():
            try:
                print('🔍 Checking ' + source_name + f' (scanning {items_to_check} items)...')
                response = requests.get(source_info['url'], timeout=15)
                
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError:
                    print('   ⚠️  RSS error')
                    continue
                
                items = root.findall('.//item')
                source_count = 0
                
                for item in items[:items_to_check]:
                    title = item.find('title')
                    title = title.text if title is not None and title.text else ''
                    
                    link = item.find('link')
                    link = link.text if link is not None and link.text else ''
                    
                    desc = item.find('description')
                    desc_text = desc.text if desc is not None and desc.text else ''
                    
                    pub_date = None
                    pub_date_raw = None
                    for date_tag in ['pubDate', 'published', 'dc:date']:
                        date_elem = item.find(date_tag)
                        if date_elem is not None and date_elem.text:
                            pub_date_raw = date_elem.text
                            pub_date = self.parse_article_date(date_elem.text)
                            break
                    
                    if pub_date_raw and not self.is_article_after_cutoff(pub_date_raw):
                        continue
                    
                    if desc_text:
                        desc_soup = BeautifulSoup(desc_text, 'html.parser')
                        desc_text = desc_soup.get_text()
                    
                    if not link or not title:
                        continue
                    
                    tottenham_sources = ['tottenhamhotspurnews', 'spurs-web', 'tothelaneandback', 'tottenhamhotspur.com']
                    is_tottenham_source = any(source in source_name.lower() for source in tottenham_sources)
                    
                    if not is_tottenham_source:
                        search_text = (title + ' ' + desc_text).lower()
                        has_tottenham = any(keyword in search_text for keyword in self.primary_keywords)
                        
                        if not has_tottenham:
                            continue
                    
                    if not self.is_primary_tottenham_story(title, desc_text, "", source_name):
                        if not is_tottenham_source:
                            print('   ⏭️  Skip: ' + title[:50] + '...')
                        continue
                    
                    article_id = self.get_article_id(link)
                    if article_id in self.seen_articles:
                        continue
                    
                    print('   ✅ ACCEPT: ' + title[:50] + '...')
                    
                    full_content, image_url = self.extract_full_article(link)
                    
                    print('      📝 Creating smart summary...')
                    smart_summary = self.create_smart_summary(title, full_content, link)
                    print(f'      ✨ Summary: {smart_summary[:100]}...')
                    
                    article_data = {
                        'source': source_name,
                        'source_homepage': source_info['homepage'],
                        'title': title,
                        'summary': smart_summary,
                        'link': link,
                        'image_url': image_url,
                        'published_date': pub_date,
                        'chars': len(smart_summary),
                        'has_full_content': bool(full_content and len(full_content) > 100),
                        'content_length': len(full_content) if full_content else 0,
                        'found_at': datetime.now().isoformat()
                    }
                    
                    new_articles.append(article_data)
                    source_count += 1
                    
                    self.seen_articles[article_id] = {
                        'title': title,
                        'found_at': datetime.now().isoformat()
                    }
                    
                    print('   💾 Saved!')
                    time.sleep(1 if self.is_initial_scan else 2)
                
                print('   🎯 ' + str(source_count) + ' stories from ' + source_name)
                
            except Exception as e:
                print('   ❌ Error: ' + str(e))
        
        return new_articles
    
    def load_existing_articles(self):
        if not os.path.exists(self.html_filename):
            return []
        
        try:
            with open('articles_data.json', 'r') as f:
                data = json.load(f)
                return data.get('articles', [])
        except:
            return []
    
    def save_all_articles(self, new_articles):
        existing_articles = self.load_existing_articles()
        all_articles = new_articles + existing_articles
        
        seen_links = set()
        unique_articles = []
        for article in all_articles:
            if article['link'] not in seen_links:
                unique_articles.append(article)
                seen_links.add(article['link'])
        
        def get_sort_date(article):
            pub_date = article.get('published_date')
            if pub_date:
                try:
                    return datetime.strptime(pub_date, '%d %B %Y, %H:%M')
                except:
                    pass
            
            found_at = article.get('found_at')
            if found_at:
                try:
                    return datetime.fromisoformat(found_at.replace('T', ' ').replace('Z', ''))
                except:
                    pass
            
            return datetime.min
        
        unique_articles.sort(key=get_sort_date, reverse=True)
        
        limit = 100 if self.is_initial_scan else 50
        unique_articles = unique_articles[:limit]
        
        with open('articles_data.json', 'w') as f:
            json.dump({
                'last_updated': datetime.now().isoformat(),
                'total_articles': len(unique_articles),
                'articles': unique_articles
            }, f, indent=2)
        
        self.create_live_html(unique_articles)
        return len(unique_articles)
    
    def create_live_html(self, articles):
        html_content = f'''<!DOCTYPE html>
<html><head>
<title>Tottenham Hotspur</title>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {{
    box-sizing: border-box;
}}

body {{ 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
    margin: 0; padding: 0; background: #f8f9fa; line-height: 1.6;
    width: 100%;
}}

.header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: 
        linear-gradient(rgba(19, 34, 87, 0.75), rgba(19, 34, 87, 0.75)),
        url('stadium.jpeg');
    background-size: cover;
    background-position: center;
    z-index: 1000;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    padding: 15px 0;
}}

.logo-container {{
    text-align: center;
    margin: 8px 0 12px 0;
}}

.team-logo {{
    height: 60px;
    width: auto;
    filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.5));
    transition: transform 0.3s ease;
}}

.team-logo:hover {{
    transform: scale(1.1);
}}

.header-content {{
    max-width: 100%;
    margin: 0 auto;
    padding: 0 15px;
}}

h1 {{ 
    color: white; text-align: center; margin: 0 0 8px 0; font-size: 2.4em; 
    text-shadow: 2px 2px 4px rgba(0,0,0,0.8); font-weight: bold;
}}

.subtitle {{ 
    text-align: center; color: white; margin: 0 0 12px 0; font-style: italic; 
    text-shadow: 1px 1px 3px rgba(0,0,0,0.8); font-size: 0.85em;
}}

.stats {{ 
    background: none; color: white; 
    padding: 8px 12px; text-align: center; 
    font-weight: normal; text-shadow: 1px 1px 3px rgba(0,0,0,0.8);
    margin: 0 15px; font-size: 0.75em;
}}

.manual-refresh {{
    background: #132257; 
    color: white; padding: 8px 16px; border-radius: 20px; 
    font-size: 0.8em; box-shadow: 0 4px 12px rgba(0,0,0,0.2); 
    cursor: pointer; transition: all 0.3s; border: none;
    margin: 12px auto 0 auto;
    display: block;
}}

.manual-refresh:hover {{
    background: #0d1a3f;
    transform: scale(1.05);
}}

.main-content {{
    margin-top: 280px;
    max-width: 100%;
    margin-left: auto;
    margin-right: auto;
    padding: 0 10px 50px 10px;
}}

.article {{ 
    background: white; margin: 20px 0; border-radius: 12px; 
    box-shadow: 0 4px 15px rgba(0,0,0,0.1); overflow: hidden; 
    border-left: 4px solid #132257; transition: transform 0.3s ease;
}}

.article:hover {{ transform: translateY(-2px); }}

.article-image {{ 
    width: 100%; height: 180px; object-fit: cover; display: block; 
}}

.article-content {{ padding: 15px; }}

.source-info {{ 
    color: #666; font-size: 0.8em; margin-bottom: 10px; font-weight: normal;
}}

.source-link {{
    color: #666;
    text-decoration: none;
    transition: opacity 0.3s;
}}

.source-link:hover {{
    opacity: 0.7;
}}

.title {{ 
    color: #132257; font-size: 1.1em; font-weight: bold; 
    margin-bottom: 12px; line-height: 1.3; 
}}

.summary {{ 
    line-height: 1.6; margin: 12px 0; color: #333; font-size: 0.95em; 
}}

.read-full-link {{
    color: #132257;
    text-decoration: none;
    font-weight: 500;
    transition: opacity 0.3s;
    display: block;
    margin-top: 12px;
    font-size: 0.9em;
}}

.read-full-link:hover {{
    opacity: 0.7;
    text-decoration: underline;
}}

.actions {{ 
    display: flex; justify-content: space-between; align-items: center; 
    margin-top: 15px; padding-top: 12px; border-top: 1px solid #eee; 
    width: 100%;
}}

.social-icons {{ 
    display: flex; 
    justify-content: space-between; 
    width: 100%;
    gap: 5px;
    align-items: center;
}}

.icon-btn {{ 
    background: none; border: none; cursor: pointer; padding: 8px 6px; 
    border-radius: 6px; transition: all 0.3s; font-size: 14px; 
    display: flex; align-items: center; justify-content: center; gap: 4px;
    color: #132257;
    flex: 1;
    min-height: 40px;
    white-space: nowrap;
}}

.icon-btn:hover {{ 
    background: #f0f4ff; 
    transform: translateY(-1px);
}}

.like-btn.liked {{ 
    background: #e3f2fd; 
}}

.save-btn.saved {{ 
    background: #e3f2fd; 
}}

@media (max-width: 480px) {{
    .main-content {{ 
        margin-top: 320px; 
        padding: 0 8px 30px 8px;
    }}
    
    h1 {{ font-size: 1.6em; }}
    
    .article {{ margin: 15px 0; }}
    
    .article-content {{ padding: 12px; }}
    
    .article-image {{ height: 160px; }}
    
    .title {{ font-size: 1.05em; }}
    
    .summary {{ font-size: 0.9em; }}
    
    .icon-btn {{
        padding: 6px 4px;
        font-size: 12px;
        min-height: 36px;
    }}
}}

@media (max-width: 320px) {{
    .main-content {{ 
        margin-top: 170px;
        padding: 0 5px 30px 5px; 
    }}
    
    .article-content {{ padding: 10px; }}
    
    .icon-btn {{
        padding: 5px 3px;
        gap: 2px;
    }}
}}
</style>
</head><body>

<div class="header">
    <div class="header-content">
        <h1>Tottenham Hotspur</h1>
<div class="logo-container">
    <img src="https://d6bvpt6ekkwt0.cloudfront.net/5faa82a8ca2f3ac7798b4570/width-200/tottenham-logo.png.webp?1675557623" alt="Tottenham Hotspur Logo" class="team-logo">
</div>
        <div class="stats" id="statsBar">
            <span id="lastUpdateTime">Last updated: {datetime.now().strftime('%d %B %Y, %H:%M')}</span>
        </div>
        <button class="manual-refresh" id="manualRefresh" onclick="manualRefresh()" title="Click to refresh">
            Refresh
        </button>
    </div>
</div>

<div class="main-content">
<div id="articlesContainer">'''

        for i, article in enumerate(articles, 1):
            article_link_escaped = article['link'].replace("'", "\\'")
            
            html_content += f'''
<div class="article">
    {f'<img src="{article["image_url"]}" alt="Article image" class="article-image" onerror="this.style.display=&quot;none&quot;">' if article.get("image_url") else ''}
    
    <div class="article-content">
        <div class="source-info">
            <a href="{article.get('source_homepage', '#')}" class="source-link" target="_blank">{article['source']}</a>{f' - {article["published_date"]}' if article.get("published_date") else ''}
        </div>
        
        <div class="title">{article['title']}</div>
        <div class="summary">{article['summary']}</div>
        
        <a href="{article['link']}" class="read-full-link" target="_blank">Read the full article here...</a>
        
        <div class="actions">
            <div class="social-icons">
                <button class="icon-btn like-btn" onclick="toggleLike(this)" title="Like">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                    </svg>
                    <span class="count">0</span>
                </button>
                <button class="icon-btn comment-btn" onclick="showComments()" title="Comment">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span>0</span>
                </button>
                <button class="icon-btn share-btn" onclick="shareArticle('{article_link_escaped}')" title="Share">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/>
                        <polyline points="16,6 12,2 8,6"/>
                        <line x1="12" y1="2" x2="12" y2="15"/>
                    </svg>
                </button>
                <button class="icon-btn save-btn" onclick="saveArticle(this)" title="Save">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
                    </svg>
                </button>
            </div>
        </div>
    </div>
</div>'''

        html_content += '''
</div>
</div>

<script>
let updateInterval;
let refreshInterval;

function startAutoUpdate() {
    updateInterval = setInterval(checkForUpdates, 30000);
    refreshInterval = setInterval(() => {
        console.log('Auto-refreshing page...');
        location.reload();
    }, 60000);
    setInterval(updateLastUpdatedTime, 60000);
}

function updateLastUpdatedTime() {
    const now = new Date();
    const timeString = now.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'long', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
    
    const lastUpdateElement = document.getElementById('lastUpdateTime');
    if (lastUpdateElement) {
        lastUpdateElement.textContent = `Last updated: ${timeString}`;
    }
}

function checkForUpdates() {
    fetch('articles_data.json?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
            const currentCount = document.querySelectorAll('.article').length;
            if (data.total_articles > currentCount) {
                console.log('New articles found, refreshing...');
                location.reload();
            }
        })
        .catch(err => {
            console.log('Update check failed:', err);
        });
}

function toggleLike(btn) {
    const svg = btn.querySelector('svg');
    const countSpan = btn.querySelector('.count');
    let count = parseInt(countSpan.textContent);
    const isLiked = btn.classList.contains('liked');
    
    if (isLiked) {
        count--;
        btn.classList.remove('liked');
        svg.setAttribute('fill', 'none');
    } else {
        count++;
        btn.classList.add('liked');
        svg.setAttribute('fill', 'currentColor');
    }
    
    countSpan.textContent = count;
}

function showComments() {
    alert('💬 Comments feature coming soon!');
}

function shareArticle(url) {
    if (navigator.share) {
        navigator.share({
            title: 'Tottenham News',
            url: url
        });
    } else {
        navigator.clipboard.writeText(url).then(() => {
            alert('📋 Link copied to clipboard!');
        });
    }
}

function saveArticle(btn) {
    const svg = btn.querySelector('svg');
    const isSaved = btn.classList.contains('saved');
    
    if (isSaved) {
        btn.classList.remove('saved');
        btn.title = 'Save';
        svg.setAttribute('fill', 'none');
    } else {
        btn.classList.add('saved');
        btn.title = 'Saved!';
        svg.setAttribute('fill', 'currentColor');
    }
}

function manualRefresh() {
    const btn = document.getElementById('manualRefresh');
    
    if (btn) {
        btn.innerHTML = 'Refreshing...';
        btn.style.background = '#666';
    }
    
    setTimeout(() => {
        location.reload();
    }, 500);
}

window.onload = function() {
    console.log('Page loaded, starting auto-update...');
    startAutoUpdate();
};
</script>

</body></html>'''
        
        with open(self.html_filename, 'w') as f:
            f.write(html_content)
    
    def run_continuous(self):
        print('🏆 TOTTENHAM LIVE NEWS SCANNER - SMART SUMMARIES')
        print('=' * 60)
        
        if self.is_initial_scan:
            print('🔄 INITIAL SCAN MODE - Deep historical search')
            print('📅 Scanning deeper (25 items per feed) for June 1st+ articles')
        else:
            print('🔄 REGULAR SCAN MODE - Recent updates only')
            print('📅 Filtering articles from 1st June 2025 onwards')
        
        print('🎯 Real-time updates with smart summarization')
        print('📝 Smart keyword-based summaries from full articles')
        print('📱 Mobile-first design optimized for apps')
        print('⏰ Checking every 1 minute for new articles')
        print('=' * 60)
        
        existing_articles = self.load_existing_articles()
        if not existing_articles:
            self.create_live_html([])
        
        while True:
            try:
                scan_type = "DEEP HISTORICAL" if self.is_initial_scan else "REGULAR"
                print(f'\n🕐 {datetime.now().strftime("%H:%M:%S")} - {scan_type} SCAN...')
                
                new_articles = self.check_for_articles()
                
                if new_articles:
                    total_count = self.save_all_articles(new_articles)
                    self.save_seen_articles()
                    
                    print(f'\n🎉 Added {len(new_articles)} new articles! Total: {total_count}')
                    print(f'📱 Updated: {self.html_filename} (Mobile optimized)')
                    
                    for article in new_articles:
                        date_info = f" ({article['published_date']})" if article.get('published_date') else ''
                        image_info = ' 🖼️' if article.get('image_url') else ''
                        summary_preview = article['summary'][:80] + '...' if len(article['summary']) > 80 else article['summary']
                        print(f'   📰{image_info} {article["title"][:40]}...{date_info}')
                        print(f'      📝 {summary_preview}')
                    
                    if self.is_initial_scan:
                        self.is_initial_scan = False
                        print('\n🔄 Switching to regular scan mode for future updates')
                else:
                    print('   ℹ️  No new stories found (after June 1st cutoff)')
                
                print(f'\n   😴 Sleeping 1 minute... (Open {self.html_filename} in browser)')
                print('-' * 60)
                time.sleep(60)
                
            except KeyboardInterrupt:
                print('\n🛑 Scanner stopped')
                break
            except Exception as e:
                print(f'❌ Error: {e}')
                time.sleep(60)

if __name__ == "__main__":
    scanner = TottenhamAIScanner()
    scanner.run_continuous()
