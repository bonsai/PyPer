/**
 * PyPer - PR Times to Gmail Pipeline
 * 
 * Google Apps Script for fetching PR Times press releases and sending via Gmail
 * 
 * Setup:
 * 1. Copy this script to Google Apps Script Editor (script.google.com)
 * 2. Set up time-driven trigger to run automatically
 * 3. Configure SETTINGS below
 */

// ==================== Settings ====================
const SETTINGS = {
  // PR Times search URL (「発表会」keyword)
  PR_TIMES_URL: 'https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E7%99%BA%E8%A1%A8%E4%BC%9A',
  
  // Email settings
  EMAIL_SUBJECT_PREFIX: '【PR Times】',
  EMAIL_RECIPIENT: 'onsen.bonsai+pr@gmail.com', // Change to your email
  
  // State storage key (Properties Service)
  STATE_KEY: 'prtimes_seen_urls',
  
  // Max press releases per run
  LIMIT: 3
};

// ==================== Main Function ====================
function main() {
  console.log('=== PyPer Pipeline Started ===');
  
  try {
    // Fetch press releases
    const pressReleases = fetchPressReleases();
    console.log(`Fetched ${pressReleases.length} press releases`);
    
    if (pressReleases.length === 0) {
      console.log('No new press releases');
      return;
    }
    
    // Send emails
    sendEmails(pressReleases);
    
    console.log('=== PyPer Pipeline Completed ===');
  } catch (error) {
    console.error(`Error: ${error.toString()}`);
    throw error;
  }
}

// ==================== Functions ====================

/**
 * Fetch press releases from PR Times
 */
function fetchPressReleases() {
  const seenUrls = getSeenUrls();
  const newPressReleases = [];
  
  try {
    // Fetch HTML
    const response = UrlFetchApp.fetch(SETTINGS.PR_TIMES_URL, {
      muteHttpExceptions: true,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      }
    });
    
    if (response.getResponseCode() !== 200) {
      throw new Error(`Failed to fetch PR Times: ${response.getResponseCode()}`);
    }
    
    const html = response.getContentText();
    
    // Parse HTML using regex (GAS doesn't have BeautifulSoup)
    const urlPattern = /<a[^>]*href="([^"]*\/main\/html\/rd\/p\/[^"]*\.html)"[^>]*>([^<]+)<\/a>/g;
    let match;
    let count = 0;
    
    while ((match = urlPattern.exec(html)) !== null && count < SETTINGS.LIMIT) {
      const url = match[1];
      const title = match[2].trim();
      
      // Skip already seen URLs
      if (seenUrls.includes(url)) {
        continue;
      }
      
      // Convert to absolute URL
      const absoluteUrl = url.startsWith('http') ? url : `https://prtimes.jp${url}`;
      
      newPressReleases.push({
        title: title,
        url: absoluteUrl,
        summary: `${title} のプレスリリースが公開されました。`,
        timestamp: new Date().toISOString()
      });
      
      seenUrls.push(url);
      count++;
    }
    
    // Save state
    saveSeenUrls(seenUrls);
    
  } catch (error) {
    console.error(`Failed to fetch press releases: ${error.toString()}`);
    throw error;
  }
  
  return newPressReleases;
}

/**
 * Send emails for press releases
 */
function sendEmails(pressReleases) {
  for (const pr of pressReleases) {
    try {
      const subject = `${SETTINGS.EMAIL_SUBJECT_PREFIX}${pr.title}`;
      
      const htmlBody = `
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
          <h2 style="color: #333;">${pr.title}</h2>
          <p style="color: #666; line-height: 1.6;">${pr.summary}</p>
          <p style="margin-top: 20px;">
            <a href="${pr.url}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">元記事を読む</a>
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin-top: 30px;">
          <p style="color: #999; font-size: 12px;">
            出典：PR Times<br>
            送信日時：${pr.timestamp}
          </p>
        </body>
        </html>
      `;
      
      GmailApp.sendEmail(
        SETTINGS.EMAIL_RECIPIENT,
        subject,
        `${pr.title}\n\n${pr.summary}\n\n元記事：${pr.url}`,
        {
          htmlBody: htmlBody,
          name: 'PyPer Bot'
        }
      );
      
      console.log(`Sent email: ${pr.title}`);
    } catch (error) {
      console.error(`Failed to send email for "${pr.title}": ${error.toString()}`);
    }
  }
}

// ==================== State Management ====================

/**
 * Get seen URLs from Properties Service
 */
function getSeenUrls() {
  const props = PropertiesService.getUserProperties();
  const data = props.getProperty(SETTINGS.STATE_KEY);
  return data ? JSON.parse(data) : [];
}

/**
 * Save seen URLs to Properties Service
 */
function saveSeenUrls(urls) {
  const props = PropertiesService.getUserProperties();
  props.setProperty(SETTINGS.STATE_KEY, JSON.stringify(urls));
}

// ==================== Setup Function ====================

/**
 * Clear stored state (for testing)
 */
function clearState() {
  const props = PropertiesService.getUserProperties();
  props.deleteProperty(SETTINGS.STATE_KEY);
  console.log('State cleared');
}

/**
 * Test run (fetches but doesn't send emails)
 */
function testRun() {
  const pressReleases = fetchPressReleases();
  console.log(`Would send ${pressReleases.length} emails:`);
  pressReleases.forEach(pr => {
    console.log(`- ${pr.title}`);
  });
}
