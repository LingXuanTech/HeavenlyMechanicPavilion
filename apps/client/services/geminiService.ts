import { GoogleGenAI, Type, Modality } from "@google/genai";
import { AgentAnalysis, SignalType, WebSource, GlobalMarketAnalysis, MarketOpportunity, FlashNews } from "../types";

const apiKey = process.env.API_KEY || '';

// Initialize the client
const ai = new GoogleGenAI({ apiKey });

export const analyzeStockWithAgent = async (symbol: string, stockName: string, currentPrice: number): Promise<AgentAnalysis> => {
  if (!apiKey) {
    console.warn("No API Key found. Returning mock analysis.");
    return mockAnalysis(symbol);
  }

  // Use gemini-3-pro-preview for Thinking Config
  const model = "gemini-3-pro-preview"; 
  const today = new Date().toISOString().split('T')[0];

  const prompt = `
    You are the "Fund Manager" AI, orchestrating a high-frequency trading team. 
    Analyze ${stockName} (${symbol}). Input Price: ${currentPrice}. Date: ${today}.

    **Objective**: Maximize Alpha, Minimize Drawdown. 
    
    **Phase 1: The Analyst Team (Data Mining)**
    Use Google Search to gather:
    - Real-time Price, RSI (14), MACD status.
    - Latest News Catalysts (Earnings, Product Launches, Regulatory).
    - **Peer Comparison**: Compare valuation (P/E, Growth) vs 2 main competitors.

    **Phase 2: The Researcher Debate (Adversarial)**
    Simulate a FIERCE debate. Do not be neutral.
    - **Bull Agent**: "I demand we buy because..." (Focus on Growth, Momentum, FOMO).
    - **Bear Agent**: "You are wrong because..." (Focus on Overvaluation, Macro Risks, Technical Breakdown).
    *Output distinct, hard-hitting arguments with evidence.*

    **Phase 3: The Risk Management Team (The Veto)**
    Ignore the profit potential. Focus ONLY on losing money.
    - What is the worst-case scenario?
    - Is liquidity sufficient?
    - Assign a Risk Score (0=Safe, 10=Crypto-like volatility).

    **Phase 4: The Fund Manager (Execution)**
    Synthesize the debate. Pick a winner.
    - Signal: Buy/Sell/Hold.
    - **Trade Setup**: Precise Entry, Take Profit, Stop Loss (Reward:Risk must be > 2.0).
    - Reasoning: Explain why you sided with the Bull or Bear.

    **Output Format**:
    Return strictly valid JSON adhering to the schema.
  `;

  try {
    const response = await ai.models.generateContent({
      model,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        // Maximize thinking for complex reasoning chains
        thinkingConfig: { thinkingBudget: 8192 }, 
        maxOutputTokens: 8192, 
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            // --- CORE SIGNAL ---
            signal: { type: Type.STRING, enum: Object.values(SignalType) },
            confidence: { type: Type.NUMBER },
            reasoning: { type: Type.STRING, description: "Fund Manager's final synthesis" },

            // --- DEBATE MODULE ---
            debate: {
              type: Type.OBJECT,
              properties: {
                bull: {
                  type: Type.OBJECT,
                  properties: {
                    thesis: { type: Type.STRING },
                    points: {
                      type: Type.ARRAY,
                      items: {
                        type: Type.OBJECT,
                        properties: {
                          argument: { type: Type.STRING },
                          evidence: { type: Type.STRING },
                          weight: { type: Type.STRING, enum: ['High', 'Medium', 'Low'] }
                        }
                      }
                    }
                  }
                },
                bear: {
                  type: Type.OBJECT,
                  properties: {
                    thesis: { type: Type.STRING },
                    points: {
                      type: Type.ARRAY,
                      items: {
                        type: Type.OBJECT,
                        properties: {
                          argument: { type: Type.STRING },
                          evidence: { type: Type.STRING },
                          weight: { type: Type.STRING, enum: ['High', 'Medium', 'Low'] }
                        }
                      }
                    }
                  }
                },
                winner: { type: Type.STRING, enum: ['Bull', 'Bear', 'Neutral'] },
                conclusion: { type: Type.STRING }
              }
            },

            // --- RISK MODULE ---
            riskAssessment: {
              type: Type.OBJECT,
              properties: {
                score: { type: Type.NUMBER, description: "0-10 scale" },
                volatilityStatus: { type: Type.STRING, enum: ['Low', 'Moderate', 'High', 'Extreme'] },
                liquidityConcerns: { type: Type.BOOLEAN },
                maxDrawdownRisk: { type: Type.STRING, description: "e.g. '-15% if support breaks'" },
                verdict: { type: Type.STRING, enum: ['Approved', 'Caution', 'Rejected'] }
              }
            },

            // --- ANALYST MODULES ---
            tradeSetup: {
              type: Type.OBJECT,
              properties: {
                entryZone: { type: Type.STRING },
                targetPrice: { type: Type.NUMBER },
                stopLossPrice: { type: Type.NUMBER },
                rewardToRiskRatio: { type: Type.NUMBER },
                invalidationCondition: { type: Type.STRING }
              }
            },
            technicalIndicators: {
              type: Type.OBJECT,
              properties: {
                rsi: { type: Type.NUMBER },
                macd: { type: Type.STRING },
                trend: { type: Type.STRING, enum: ['Bullish', 'Bearish', 'Neutral'] }
              }
            },
            priceLevels: {
              type: Type.OBJECT,
              properties: {
                support: { type: Type.NUMBER },
                resistance: { type: Type.NUMBER }
              }
            },
            macroContext: {
               type: Type.OBJECT,
               properties: {
                 relevantIndex: { type: Type.STRING },
                 correlation: { type: Type.STRING },
                 environment: { type: Type.STRING },
                 summary: { type: Type.STRING }
               }
            },
            newsAnalysis: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  headline: { type: Type.STRING },
                  sentiment: { type: Type.STRING },
                  summary: { type: Type.STRING }
                }
              }
            },
            catalysts: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING },
                  date: { type: Type.STRING },
                  impact: { type: Type.STRING }
                }
              }
            },
            peers: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING },
                  comparison: { type: Type.STRING }
                }
              }
            }
          }
        }
      }
    });

    const text = response.text;
    if (!text) throw new Error("Empty response from Gemini");
    
    let data;
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.error("Failed to parse JSON response", text);
      throw new Error("Invalid JSON response from model");
    }
    
    // Extract grounding chunks
    const webSources: WebSource[] = [];
    const groundingChunks = response.candidates?.[0]?.groundingMetadata?.groundingChunks;
    
    if (groundingChunks) {
      groundingChunks.forEach((chunk: any) => {
        if (chunk.web?.uri && chunk.web?.title) {
          webSources.push({
            uri: chunk.web.uri,
            title: chunk.web.title
          });
        }
      });
    }

    const uniqueSources = Array.from(new Map(webSources.map(item => [item.uri, item])).values());

    return {
      symbol,
      timestamp: new Date().toLocaleTimeString(),
      ...data,
      webSources: uniqueSources
    };

  } catch (error) {
    console.error("Gemini Analysis Failed:", error);
    return mockAnalysis(symbol);
  }
};

export const analyzeGlobalMarket = async (): Promise<GlobalMarketAnalysis> => {
  if (!apiKey) {
    console.warn("No API Key found. Returning mock market data.");
    return {
      sentiment: "Neutral",
      summary: "Mock Data: Market is mixed as API key is missing.",
      indices: [
        { name: "S&P 500", value: 5000, change: 0, changePercent: 0 },
        { name: "HSI", value: 17000, change: 0, changePercent: 0 }
      ],
      lastUpdated: new Date().toLocaleTimeString()
    };
  }

  const model = "gemini-3-pro-preview";
  const prompt = `
    Find the latest real-time prices, point change, and percentage change for these indices:
    1. S&P 500
    2. Nasdaq 100
    3. Hang Seng Index (HSI)
    4. CSI 300
    5. Bitcoin (BTC/USD)

    Also, summarize the overall global market sentiment in one sentence (e.g. 'Tech rally drives markets higher' or 'Inflation fears weigh on stocks').
    Determine if the sentiment is Bullish, Bearish, Neutral, or Mixed.

    Output pure JSON.
  `;

  try {
    const response = await ai.models.generateContent({
      model,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            sentiment: { type: Type.STRING, enum: ['Bullish', 'Bearish', 'Neutral', 'Mixed'] },
            summary: { type: Type.STRING },
            indices: {
              type: Type.ARRAY,
              items: {
                type: Type.OBJECT,
                properties: {
                  name: { type: Type.STRING },
                  value: { type: Type.NUMBER },
                  change: { type: Type.NUMBER },
                  changePercent: { type: Type.NUMBER }
                }
              }
            }
          }
        }
      }
    });

    const text = response.text;
    if (!text) throw new Error("Empty response");
    const data = JSON.parse(text);

    return {
      ...data,
      lastUpdated: new Date().toLocaleTimeString()
    };

  } catch (error) {
    console.error("Market Analysis Failed:", error);
    return {
      sentiment: "Neutral",
      summary: "Failed to fetch market data.",
      indices: [],
      lastUpdated: new Date().toLocaleTimeString()
    };
  }
};

// --- THE SCOUT AGENT (Scanner) ---
export const scoutMarketOpportunities = async (query: string): Promise<MarketOpportunity[]> => {
  if (!apiKey) return [];

  const model = "gemini-3-pro-preview";
  const prompt = `
    Act as a Market Scanner (Scout). The user is looking for new investment opportunities.
    Query: "${query}"

    Task:
    1. Use Google Search to find stocks that match the user's request (e.g. "undervalued tech stocks HK", "US AI stocks breaking out").
    2. Return 3-5 specific stock tickers.
    3. Identify the correct market (US, HK, CN).
    4. Provide a brief 1-sentence reason why this fits the query.
    5. Assign a relevance score (1-10).

    Output pure JSON.
  `;

  try {
    const response = await ai.models.generateContent({
      model,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              symbol: { type: Type.STRING },
              name: { type: Type.STRING },
              market: { type: Type.STRING, enum: ['US', 'HK', 'CN'] },
              reason: { type: Type.STRING },
              score: { type: Type.NUMBER }
            }
          }
        }
      }
    });

    const text = response.text;
    if (!text) return [];
    return JSON.parse(text);
  } catch (error) {
    console.error("Scout Agent Failed:", error);
    return [];
  }
};

// --- THE WATCHDOG AGENT (Flash News) ---
export const getFlashNews = async (): Promise<FlashNews[]> => {
  if (!apiKey) return [];

  const model = "gemini-3-flash-preview"; // Fast model for news
  const prompt = `
    Find the top 5 "Breaking Financial News" headlines from the last hour impacting global markets (US/HK/CN).
    Focus on major movers, earnings, or macro events.
    
    Output pure JSON.
  `;

  try {
    const response = await ai.models.generateContent({
      model,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.ARRAY,
          items: {
            type: Type.OBJECT,
            properties: {
              id: { type: Type.STRING, description: "Unique ID e.g. timestamp" },
              time: { type: Type.STRING, description: "Time e.g. '10:30 AM'" },
              headline: { type: Type.STRING },
              impact: { type: Type.STRING, enum: ['High', 'Medium', 'Low'] },
              sentiment: { type: Type.STRING, enum: ['Positive', 'Negative'] },
              relatedSymbols: { type: Type.ARRAY, items: { type: Type.STRING } }
            }
          }
        }
      }
    });

    const text = response.text;
    if (!text) return [];
    return JSON.parse(text);
  } catch (error) {
    console.error("Watchdog Agent Failed:", error);
    return [];
  }
};

export const getChatResponse = async (
  message: string, 
  context: { symbol: string, analysis: AgentAnalysis },
  history: { role: 'user' | 'model', text: string }[]
): Promise<string> => {
  if (!apiKey) return "Chat unavailable in mock mode (No API Key).";

  const model = "gemini-3-flash-preview";
  
  const systemInstruction = `
    You are a professional stock trading assistant discussing the stock ${context.symbol}.
    Analysis Context:
    - Signal: ${context.analysis.signal}
    - Reasoning: ${context.analysis.reasoning}
    - Debate Winner: ${context.analysis.debate?.winner}
    
    Answer concisely. Focus on risk management.
  `;

  try {
    const chat = ai.chats.create({
      model,
      config: { systemInstruction },
      history: history.map(h => ({
        role: h.role,
        parts: [{ text: h.text }]
      }))
    });

    const result = await chat.sendMessage({ message });
    return result.text || "I couldn't generate a response.";
  } catch (error) {
    console.error("Chat Error:", error);
    return "Sorry, I encountered an error connecting to the agent.";
  }
};

// --- TTS Functionality ---

function decode(base64: string) {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

async function decodeAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number,
  numChannels: number,
): Promise<AudioBuffer> {
  const dataInt16 = new Int16Array(data.buffer);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

export const playAudioBriefing = async (symbol: string, analysisText: string): Promise<void> => {
  if (!apiKey) {
    console.warn("TTS unavailable without API Key");
    return;
  }

  const prompt = `
    You are a financial news anchor. Read this stock analysis for ${symbol} as a quick 30-second briefing.
    Analysis: ${analysisText}
  `;

  try {
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash-preview-tts",
      contents: [{ parts: [{ text: prompt }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: 'Kore' }, 
            },
        },
      },
    });

    const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (!base64Audio) throw new Error("No audio data returned");

    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    const audioContext = new AudioContextClass({ sampleRate: 24000 });
    
    const audioBytes = decode(base64Audio);
    const audioBuffer = await decodeAudioData(audioBytes, audioContext, 24000, 1);
    
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioContext.destination);
    source.start();

  } catch (error) {
    console.error("TTS generation failed:", error);
    throw error;
  }
};

const mockAnalysis = (symbol: string): AgentAnalysis => {
  const r = Math.random();
  const scenario = r > 0.6 ? 'bull' : r > 0.3 ? 'bear' : 'neutral';
  
  const isBullish = scenario === 'bull';
  const isBearish = scenario === 'bear';
  const basePrice = 100;

  return {
    symbol,
    timestamp: new Date().toLocaleTimeString(),
    signal: isBullish ? SignalType.BUY : isBearish ? SignalType.SELL : SignalType.HOLD,
    confidence: Math.floor(Math.random() * 30) + 60,
    reasoning: `**Mock Analysis (Offline)**: Unable to connect to Gemini Agent. \n\n# Synthesis \nThis is a simulated ${scenario} scenario generated for testing purposes.`,
    debate: {
      bull: { 
        thesis: "Strong Growth & Momentum", 
        points: [
          { argument: "Revenue growth accelerating Q/Q", evidence: "Q3 Report", weight: "High" },
          { argument: "Sector rotation favoring tech", evidence: "Market Trends", weight: "Medium" }
        ] 
      },
      bear: { 
        thesis: "Valuation Concerns", 
        points: [
          { argument: "P/E Ratio at historic highs", evidence: "Financials", weight: "High" },
          { argument: "Macro headwinds persisting", evidence: "Fed Policy", weight: "Medium" }
        ] 
      },
      winner: isBullish ? 'Bull' : isBearish ? 'Bear' : 'Neutral',
      conclusion: isBullish ? "Growth potential outweighs valuation risks." : isBearish ? "Downside risk is too high to ignore." : "Market is directionless, wait for clarity."
    },
    riskAssessment: {
      score: isBearish ? 8 : isBullish ? 3 : 5,
      volatilityStatus: isBearish ? 'High' : 'Moderate',
      liquidityConcerns: false,
      maxDrawdownRisk: isBearish ? "-15%" : "-5%",
      verdict: isBearish ? 'Caution' : 'Approved'
    },
    catalysts: [
      { name: "Q3 Earnings", date: "2024-10-15", impact: "Positive" },
      { name: "Product Launch", date: "2024-11-01", impact: "Neutral" }
    ],
    priceLevels: {
      support: basePrice * 0.95,
      resistance: basePrice * 1.05
    },
    technicalIndicators: {
      rsi: isBullish ? 45 : 65,
      macd: "Converging",
      trend: isBullish ? 'Bullish' : 'Neutral'
    },
    newsAnalysis: [
        { headline: "Sector sees unexpected growth", sentiment: "Positive", summary: "Analysts upgrade sector outlook." },
        { headline: "New regulations pending", sentiment: "Negative", summary: "Govt discussing tighter controls." }
    ],
    peers: [
        { name: "Competitor A", comparison: "Lagging in performance" },
        { name: "Competitor B", comparison: "High correlation" }
    ],
    tradeSetup: {
      entryZone: "98.50 - 99.50",
      targetPrice: 110.00,
      stopLossPrice: 95.00,
      rewardToRiskRatio: 2.8,
      invalidationCondition: "Daily close below 200 EMA"
    },
    macroContext: {
      relevantIndex: "S&P 500",
      correlation: "High",
      environment: isBullish ? "Tailwind" : "Headwind",
      summary: "Broad market rally supporting high beta stocks."
    },
    webSources: []
  };
};