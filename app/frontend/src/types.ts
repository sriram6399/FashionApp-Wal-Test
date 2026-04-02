export type LocationContext = {
  continent: string | null;
  country: string | null;
  city: string | null;
};

export type TimeContext = {
  year: number | null;
  month: number | null;
  season: string | null;
};

export type StructuredMeta = {
  garment_type: string | null;
  style: string | null;
  material: string | null;
  color_palette: string[];
  pattern: string | null;
  season: string | null;
  occasion: string | null;
  consumer_profile: string | null;
  trend_notes: string | null;
  location_context: LocationContext | null;
  time_context: TimeContext | null;
};

export type ImageItem = {
  id: number;
  description: string;
  structured: StructuredMeta;
  designer_tags: string[];
  designer_notes: string | null;
  designer_name: string | null;
  file_url: string;
  created_at: string;
};

export type FilterOptions = {
  garment_type: string[];
  style: string[];
  material: string[];
  color_palette: string[];
  pattern: string[];
  season: string[];
  occasion: string[];
  consumer_profile: string[];
  trend_notes: string[];
  continent: string[];
  country: string[];
  city: string[];
  year: number[];
  month: number[];
  time_season: string[];
  designer_name: string[];
  designer_tags: string[];
};
