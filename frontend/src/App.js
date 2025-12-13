import { useState } from "react";
import "@/App.css";
import { Flame, Download, Share2, Loader2 } from "lucide-react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast, Toaster } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [roastStyle, setRoastStyle] = useState("mix");
  const [loading, setLoading] = useState(false);
  const [roastData, setRoastData] = useState(null);
  const [loadingText, setLoadingText] = useState("");
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const loadingMessages = [
    "Stalking their profile...",
    "Finding cringe content...",
    "Preparing emotional damage...",
    "Cooking up the roast...",
    "Adding masala to the roast..."
  ];

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
    if (roastData) {
      if (navigator.share) {
        try {
          await navigator.share({
            title: "LinkedIn Roast",
            text: roastData.roast_text,
          });
        } catch (err) {
          console.error("Share failed:", err);
        }
      } else {
        navigator.clipboard.writeText(roastData.roast_text);
        toast.success("Roast copied to clipboard!");
      }
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
          <div className="text-center mb-12">
            <div className="flex items-center justify-center gap-4 mb-6">
              <Flame className="w-16 h-16 text-[#FF2E00] animate-pulse" data-testid="flame-icon" />
              <h1
                className="text-6xl font-bold uppercase tracking-widest text-white"
                style={{ fontFamily: "'Anton', sans-serif" }}
                data-testid="app-title"
              >
                THE ROAST
              </h1>
              <Flame className="w-16 h-16 text-[#FF2E00] animate-pulse" />
            </div>
            <h2 className="text-xl text-[#666666] uppercase tracking-wider">
              TERMINAL
            </h2>
            <p className="text-sm text-[#666666] mt-4">
              Enter karo LinkedIn profile, roast ready karo
            </p>
          </div>

          {!roastData && (
            <div className="bg-[#0A0A0A] border border-white/10 p-8 mb-8" data-testid="input-section">
              <div className="mb-6">
                <label className="block text-sm mb-2 uppercase tracking-wider text-[#E0E0E0]">
                  LinkedIn Profile URL
                </label>
                <Input
                  data-testid="linkedin-url-input"
                  type="url"
                  placeholder="https://www.linkedin.com/in/username"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  className="h-16 text-xl bg-black border-b-2 border-white/20 focus:border-[#FF2E00] focus:ring-0 rounded-none placeholder:text-white/20"
                  disabled={loading}
                />
              </div>

              <div className="mb-8">
                <label className="block text-sm mb-4 uppercase tracking-wider text-[#E0E0E0]">
                  Roast Style
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
                      className={`p-4 border-2 transition-all duration-100 uppercase tracking-widest text-sm ${
                        roastStyle === style.value
                          ? "border-[#FF2E00] bg-[#FF2E00] text-white"
                          : "border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#FF2E00] hover:scale-105"
                      }`}
                      disabled={loading}
                    >
                      <div className="text-2xl mb-2">{style.emoji}</div>
                      {style.label}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                data-testid="generate-roast-btn"
                onClick={handleGenerateRoast}
                disabled={loading}
                className="w-full h-16 text-lg rounded-none border-2 border-[#FF2E00] bg-transparent text-[#FF2E00] hover:bg-[#FF2E00] hover:text-white transition-all duration-100 uppercase tracking-widest shadow-[0_0_20px_rgba(255,46,0,0.3)] hover:shadow-[0_0_40px_rgba(255,46,0,0.6)]"
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    {loadingText}
                  </>
                ) : (
                  "GENERATE ROAST"
                )}
              </Button>
            </div>
          )}

          {roastData && (
            <div className="space-y-6" data-testid="roast-result">
              <div className="bg-[#0A0A0A] border border-white/10 p-8">
                <div className="flex items-center gap-3 mb-6">
                  <div className="text-4xl">🔥</div>
                  <h3
                    className="text-3xl uppercase tracking-wider text-[#FF2E00]"
                    style={{ fontFamily: "'Anton', sans-serif" }}
                  >
                    ROASTED
                  </h3>
                </div>

                <div className="mb-8 min-h-[200px]" data-testid="roast-text">
                  {isPlaying ? (
                    <div className="space-y-4">
                      {roastData.roast_lines.map((line, index) => (
                        <div
                          key={index}
                          className={`text-xl leading-relaxed transition-all duration-500 ${
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
                    <div className="text-[#E0E0E0] leading-relaxed text-lg whitespace-pre-wrap">
                      {roastData.roast_text}
                    </div>
                  )}
                </div>

                <div className="bg-black/50 border border-white/10 p-6">
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
              </div>

              <div className="flex gap-4">
                <Button
                  data-testid="download-btn"
                  onClick={handleDownload}
                  className="flex-1 h-14 rounded-none border-2 border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#7000FF] hover:bg-[#7000FF] hover:text-white transition-all duration-100 uppercase tracking-widest"
                >
                  <Download className="mr-2 h-5 w-5" />
                  DOWNLOAD
                </Button>
                <Button
                  data-testid="share-btn"
                  onClick={handleShare}
                  className="flex-1 h-14 rounded-none border-2 border-white/20 bg-transparent text-[#E0E0E0] hover:border-[#00FF94] hover:bg-[#00FF94] hover:text-black transition-all duration-100 uppercase tracking-widest"
                >
                  <Share2 className="mr-2 h-5 w-5" />
                  SHARE
                </Button>
              </div>

              <Button
                data-testid="roast-another-btn"
                onClick={() => {
                  setRoastData(null);
                  setLinkedinUrl("");
                }}
                className="w-full h-14 rounded-none border-2 border-[#FF2E00] bg-transparent text-[#FF2E00] hover:bg-[#FF2E00] hover:text-white transition-all duration-100 uppercase tracking-widest"
              >
                ROAST ANOTHER PROFILE
              </Button>
            </div>
          )}
        </div>
      </div>

      <Toaster position="top-center" theme="dark" />
    </div>
  );
}

export default App;