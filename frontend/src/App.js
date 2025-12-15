import { useState } from "react";
import "@/App.css";
import { Flame, Download, Share2, Loader2 } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast, Toaster } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const SITE_URL = process.env.REACT_APP_SITE_URL || window.location.origin;
const API = `${BACKEND_URL}/api`;

function App() {
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [roastStyle, setRoastStyle] = useState("savage");
  const [loading, setLoading] = useState(false);
  const [roastData, setRoastData] = useState(null);
  const [loadingText, setLoadingText] = useState("");
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showTipPopup, setShowTipPopup] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [rating, setRating] = useState(0);
  const [feedbackText, setFeedbackText] = useState("");

  const loadingMessages = [
    "Stalking their profile...",
    "Finding cringe content...",
    "Preparing emotional damage...",
    "Cooking up the roast...",
    "Adding masala to the roast..."
  ];

  const handleFeedbackSubmit = async () => {
    if (rating === 0) {
      toast.error('Please select a rating');
      return;
    }
    
    try {
      await axios.post(`${API}/submit-rating`, {
        rating: rating,
        feedback_text: feedbackText,
      });
      setShowFeedback(false);
      setRating(0);
      setFeedbackText("");
      localStorage.setItem('feedbackGiven', 'true');
      toast.success('Thanks for your feedback! 🙏');
    } catch (error) {
      console.error('Feedback error:', error);
      setShowFeedback(false);
      setRating(0);
      setFeedbackText("");
      toast.success('Thanks! 🙏');
    }
  };

  const handleGenerateRoast = async () => {
    if (!linkedinUrl.trim()) {
      toast.error("Please enter a LinkedIn URL");
      return;
    }

    setLoading(true);
    setRoastData(null);
    
    let messageIndex = 0;
    setLoadingText(loadingMessages[0]);
    const loadingInterval = setInterval(() => {
      messageIndex = (messageIndex + 1) % loadingMessages.length;
      setLoadingText(loadingMessages[messageIndex]);
    }, 3000);

    try {
      const response = await axios.post(`${API}/generate-roast`, {
        linkedin_url: linkedinUrl,
        roast_style: roastStyle,
      });

      clearInterval(loadingInterval);
      setRoastData(response.data);
      toast.success("ROASTED! 🔥");
      
      // Increment roast counter and check if should show tip popup
      const roastCount = parseInt(localStorage.getItem('roastCount') || '0') + 1;
      localStorage.setItem('roastCount', roastCount.toString());
      
      // Show tip popup after 3 roasts
      if (roastCount >= 3 && !localStorage.getItem('tipShown')) {
        setTimeout(() => setShowTipPopup(true), 2000);
      }
    } catch (error) {
      clearInterval(loadingInterval);
      console.error("Error:", error);
      toast.error(error.response?.data?.detail || "Failed to generate roast");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (roastData) {
      const link = document.createElement("a");
      link.href = `${BACKEND_URL}${roastData.audio_url}`;
      const extension = roastData.audio_url.endsWith('.mp3') ? 'mp3' : 
                       roastData.audio_url.endsWith('.wav') ? 'wav' : 'mp3';
      link.download = `roast_${Date.now()}.${extension}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success("Download started!");
    }
  };

  const handleShare = async () => {
    const shareText = `🔥 Just got roasted on LinkedIn Roast!\n\nThink your LinkedIn profile can handle the heat? Get brutally honest AI-powered roasts with voice narration.\n\nTry it: ${SITE_URL}`;
    const shareTitle = "LinkedIn Roast - Get Your Profile Roasted!";
    
    try {
      // Try native share first
      if (navigator.share) {
        await navigator.share({
          title: shareTitle,
          text: shareText,
        });
        return;
      }
    } catch (err) {
      console.error("Share failed:", err);
    }
    
    // Fallback: clipboard with focus management
    try {
      window.focus();
      await navigator.clipboard.writeText(shareText);
      toast.success("Link copied to clipboard!");
    } catch (clipboardErr) {
      console.error("Clipboard failed:", clipboardErr);
      // Last resort: old-school copy
      const textArea = document.createElement('textarea');
      textArea.value = shareText;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
        toast.success("Link copied to clipboard!");
      } catch (err) {
        toast.error("Please manually copy the link");
      }
      document.body.removeChild(textArea);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-[#E0E0E0] font-mono relative overflow-hidden">
      <div
        className="absolute inset-0 opacity-5 pointer-events-none"
        style={{
          backgroundImage: 'url("https://images.unsplash.com/photo-1698376146545-5acb1bc8ea80?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzZ8MHwxfHNlYXJjaHwzfHxkYXJrJTIwZ3J1bmdlJTIwdGV4dHVyZSUyMGFic3RyYWN0fGVufDB8fHx8MTc2NTYzODczMXww&ixlib=rb-4.1.0&q=85")',
          backgroundSize: "cover",
        }}
      />

      <div className="relative z-10">
        <div className="container mx-auto px-4 py-12 max-w-4xl">
          <div className="text-center mb-6 md:mb-10">
            <div className="flex items-center justify-center gap-2 md:gap-4">
              <Flame className="w-10 h-10 md:w-16 md:h-16 text-[#FF2E00] animate-pulse" data-testid="flame-icon" />
              <h1
                className="text-3xl md:text-6xl font-bold uppercase tracking-widest text-white"
                style={{ fontFamily: "'Anton', sans-serif" }}
                data-testid="app-title"
              >
                LINKEDIN ROAST
              </h1>
              <Flame className="w-10 h-10 md:w-16 md:h-16 text-[#FF2E00] animate-pulse" />
            </div>
          </div>

          {!roastData && (
            <div className="bg-[#0A0A0A] border border-white/10 p-4 md:p-8 mb-8" data-testid="input-section">
              <div className="mb-4 md:mb-6">
                <label className="block text-xs md:text-sm mb-2 uppercase tracking-wider text-[#E0E0E0]">
                  LinkedIn Profile URL
                </label>
                <Input
                  data-testid="linkedin-url-input"
                  type="url"
                  placeholder="https://www.linkedin.com/in/username"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  className="h-12 md:h-16 text-base md:text-xl bg-black border-b-2 border-white/20 focus:border-[#FF2E00] focus:ring-0 rounded-none placeholder:text-white/20"
                  disabled={loading}
                />
              </div>

              <div className="mb-6 md:mb-8">
                <label className="block text-xs md:text-sm mb-3 md:mb-4 uppercase tracking-wider text-[#E0E0E0]">
                  Roast Style
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 md:gap-3">
                  {[
                    { value: "savage", label: "SAVAGE", emoji: "💀" },
                    { value: "funny", label: "FUNNY", emoji: "😂" },
                    { value: "witty", label: "WITTY", emoji: "🧠" },
                    { value: "mix", label: "MIX ALL", emoji: "🔥" },
                  ].map((style) => (
                    <button
                      key={style.value}
                      data-testid={`roast-style-${style.value}`}
                      onClick={() => setRoastStyle(style.value)}
                      className={`p-2 md:p-4 border-2 transition-all duration-100 uppercase tracking-widest text-xs md:text-sm ${
                        roastStyle === style.value
                          ? "border-[#FF2E00] bg-[#FF2E00] text-white"
                          : "border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#FF2E00] hover:scale-105"
                      }`}
                      disabled={loading}
                    >
                      <div className="text-xl md:text-2xl mb-1 md:mb-2">{style.emoji}</div>
                      {style.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                data-testid="generate-roast-btn"
                onClick={handleGenerateRoast}
                disabled={loading}
                className="w-full h-12 md:h-16 text-sm md:text-lg rounded-none border-2 border-[#FF2E00] bg-transparent text-[#FF2E00] hover:bg-[#FF2E00] hover:text-white transition-all duration-100 uppercase tracking-widest shadow-[0_0_20px_rgba(255,46,0,0.3)] hover:shadow-[0_0_40px_rgba(255,46,0,0.6)]"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 md:h-5 w-4 md:w-5 animate-spin" />
                    <span className="text-xs md:text-sm">{loadingText}</span>
                  </>
                ) : (
                  "GENERATE ROAST"
                )}
              </Button>
            </div>
          )}

          {roastData && (
            <div className="space-y-6 pb-40 md:pb-32" data-testid="roast-result">
              <div className="bg-[#0A0A0A] border border-white/10 p-4 md:p-8">
                <div className="flex items-center gap-2 md:gap-3 mb-4 md:mb-6">
                  <div className="text-2xl md:text-4xl">🔥</div>
                  <h3
                    className="text-xl md:text-3xl uppercase tracking-wider text-[#FF2E00]"
                    style={{ fontFamily: "'Anton', sans-serif" }}
                  >
                    ROASTED
                  </h3>
                </div>

                <div className="mb-6 md:mb-8 min-h-[150px] md:min-h-[200px]" data-testid="roast-text">
                  {isPlaying ? (
                    <div className="space-y-3 md:space-y-4">
                      {roastData.roast_lines.map((line, index) => (
                        <div
                          key={index}
                          className={`text-base md:text-xl leading-relaxed transition-all duration-500 ${
                            index <= currentLineIndex
                              ? "text-[#FF2E00] opacity-100 scale-100"
                              : "text-[#666666] opacity-30 scale-95"
                          }`}
                        >
                          {line}.
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[#E0E0E0] leading-relaxed text-base md:text-lg whitespace-pre-wrap">
                      {roastData.roast_text}
                    </div>
                  )}
                </div>
              </div>

              {/* Sticky Audio Controls at Bottom */}
              <div className="fixed bottom-0 left-0 right-0 bg-[#0A0A0A] border-t-2 border-[#FF2E00] shadow-[0_-10px_40px_rgba(255,46,0,0.3)] z-50">
                <div className="container mx-auto max-w-4xl">
                  <div className="bg-black/80 border-2 border-[#FF2E00]/50 p-4 md:p-6 m-4">
                    <audio
                      data-testid="roast-audio-player"
                      controls
                      src={`${BACKEND_URL}${roastData.audio_url}`}
                      className="w-full"
                      style={{
                        filter: "invert(1) hue-rotate(180deg)",
                      }}
                      onPlay={() => {
                        setIsPlaying(true);
                        setCurrentLineIndex(0);
                        const duration = roastData.roast_lines.length * 3;
                        roastData.roast_lines.forEach((_, index) => {
                          setTimeout(() => {
                            setCurrentLineIndex(index);
                          }, (index * duration * 1000) / roastData.roast_lines.length);
                        });
                      }}
                      onPause={() => setIsPlaying(false)}
                      onEnded={() => {
                        setIsPlaying(false);
                        setCurrentLineIndex(roastData.roast_lines.length - 1);
                      }}
                    />
                  </div>

                  <div className="flex gap-3 px-4 pb-4">
                    <Button
                      data-testid="share-btn"
                      onClick={handleShare}
                      className="flex-1 h-12 md:h-14 rounded-none border-2 border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#00FF94] hover:bg-[#00FF94] hover:text-black transition-all duration-100 uppercase tracking-widest text-xs md:text-sm"
                    >
                      <Share2 className="mr-2 h-4 w-4" />
                      SHARE
                    </Button>
                    <Button
                      data-testid="rate-btn"
                      onClick={() => setShowFeedback(true)}
                      className="flex-1 h-12 md:h-14 rounded-none border-2 border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#FFB800] hover:bg-[#FFB800] hover:text-black transition-all duration-100 uppercase tracking-widest text-xs md:text-sm"
                    >
                      <span className="mr-2">⭐</span>
                      RATE US
                    </Button>
                  </div>
                  
                  {/* Footer on Roast Page */}
                  <div className="border-t border-white/10 py-3 text-center">
                    <p className="text-xs text-[#666666]">
                      Created by{" "}
                      <a
                        href="https://www.linkedin.com/in/anshul-shivhare/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#FF2E00] hover:text-white transition-colors inline-flex items-center gap-1"
                      >
                        Anshul
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                        </svg>
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-16 pb-24 md:pb-16 border-t border-white/10 pt-8">
          <div className="text-center">
            <p className="text-xs md:text-sm text-[#666666]">
              Created by{" "}
              <a
                href="https://www.linkedin.com/in/anshul-shivhare/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#FF2E00] hover:text-white transition-colors inline-flex items-center gap-1"
              >
                Anshul
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
                </svg>
              </a>
            </p>
          </div>
        </footer>
      </div>

      <Toaster position="top-center" theme="dark" />
      
      {/* Rating Popup Modal */}
      {showFeedback && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[100] p-4">
          <div className="bg-[#0A0A0A] border-2 border-[#FF2E00] p-6 md:p-8 max-w-md w-full relative">
            <button
              onClick={() => {
                setShowFeedback(false);
                setRating(0);
                setFeedbackText("");
              }}
              className="absolute top-4 right-4 text-[#666666] hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <h3 className="text-xl md:text-2xl font-bold text-[#FF2E00] mb-4 uppercase tracking-wider" style={{ fontFamily: "'Anton', sans-serif" }}>
              RATE US 🔥
            </h3>
            
            <p className="text-[#E0E0E0] mb-4 text-sm md:text-base">
              How was your roast experience?
            </p>
            
            {/* Star Rating */}
            <div className="flex gap-2 mb-6 justify-center">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setRating(star)}
                  className="text-4xl hover:scale-110 transition-transform"
                >
                  {star <= rating ? '⭐' : '☆'}
                </button>
              ))}
            </div>
            
            {/* Optional Feedback Text */}
            <div className="mb-6">
              <label className="block text-xs text-[#AAAAAA] mb-2 uppercase tracking-wider">
                Additional Feedback (Optional)
              </label>
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Tell us more..."
                className="w-full h-24 bg-black/50 border border-white/20 p-3 text-[#E0E0E0] text-sm resize-none focus:border-[#FF2E00] focus:outline-none"
              />
            </div>
            
            {/* Submit Button */}
            <Button
              onClick={handleFeedbackSubmit}
              disabled={rating === 0}
              className="w-full h-12 rounded-none border-2 border-[#FF2E00] bg-transparent text-[#FF2E00] hover:bg-[#FF2E00] hover:text-white transition-all duration-100 uppercase tracking-widest text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              SUBMIT RATING
            </Button>
            
            <button
              onClick={() => {
                setShowFeedback(false);
                setRating(0);
                setFeedbackText("");
              }}
              className="w-full mt-3 text-xs text-[#666666] hover:text-[#AAAAAA] transition-colors"
            >
              Maybe later
            </button>
          </div>
        </div>
      )}
      
      {/* Tip Popup */}
      {showTipPopup && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-[100] p-4">
          <div className="bg-[#0A0A0A] border-2 border-[#FF2E00] p-6 md:p-8 max-w-md w-full relative">
            <button
              onClick={() => {
                setShowTipPopup(false);
                localStorage.setItem('tipShown', 'true');
              }}
              className="absolute top-4 right-4 text-[#666666] hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            
            <h3 className="text-xl md:text-2xl font-bold text-[#FF2E00] mb-4 uppercase tracking-wider" style={{ fontFamily: "'Anton', sans-serif" }}>
              Hey! 🔥
            </h3>
            
            <p className="text-[#E0E0E0] mb-4 text-sm md:text-base">
              Looks like you're enjoying the roasts 😄
            </p>
            
            <p className="text-[#AAAAAA] mb-6 text-sm">
              If this has been fun, a small tip helps keep the site running.
            </p>
            
            <div className="bg-black/50 border border-white/20 p-4 rounded flex items-center justify-between mb-6">
              <div>
                <div className="text-xs text-[#666666] mb-1">UPI ID</div>
                <div className="text-[#E0E0E0] font-mono">anshul.sbi1@ybl</div>
              </div>
              <Button
                onClick={() => {
                  navigator.clipboard.writeText('anshul.sbi1@ybl');
                  toast.success('UPI ID copied!');
                }}
                className="h-10 px-4 rounded-none border border-[#FF2E00] bg-transparent text-[#FF2E00] hover:bg-[#FF2E00] hover:text-white transition-all duration-100 text-xs uppercase tracking-wider"
              >
                COPY
              </Button>
            </div>
            
            <Button
              onClick={() => {
                setShowTipPopup(false);
                localStorage.setItem('tipShown', 'true');
              }}
              className="w-full h-12 rounded-none border-2 border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#FF2E00] hover:text-[#FF2E00] transition-all duration-100 uppercase tracking-widest text-sm"
            >
              MAYBE LATER
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;