import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Upload,
  X,
  MapPin,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { issuesApi } from "@/lib/api";

const categories = [
  { value: "facilities", label: "Facilities" },
  { value: "it-infrastructure", label: "IT Infrastructure" },
  { value: "plumbing", label: "Plumbing" },
  { value: "electrical", label: "Electrical" },
  { value: "equipment", label: "Equipment" },
  { value: "safety", label: "Safety" },
  { value: "maintenance", label: "Maintenance" },
  { value: "other", label: "Other" },
];


const priorityOptions = [
  { value: "low", label: "Low", icon: Info, color: "text-info" },
  { value: "medium", label: "Medium", icon: AlertTriangle, color: "text-warning" },
  { value: "high", label: "High", icon: AlertTriangle, color: "text-destructive" },
  { value: "critical", label: "Critical", icon: AlertCircle, color: "text-destructive" },
];

export default function ReportIssue() {
  const [images, setImages] = useState<string[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    priority: '',
    location: '',
  });
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  }, []);

  const handleFiles = (files: File[]) => {
    const imageFiles = files.filter((file) => file.type.startsWith("image/"));
    const newImages = imageFiles.map((file) => URL.createObjectURL(file));
    setImages((prev) => [...prev, ...newImages].slice(0, 5));
  };

  const removeImage = (index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title || !formData.description || !formData.category || !formData.priority || !formData.location) {
      toast({
        title: "Missing Information",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await issuesApi.createIssue({
        title: formData.title,
        description: formData.description,
        category: formData.category,
        priority: formData.priority,
        location: formData.location,
      });

      if (result.error) {
        throw new Error(result.error);
      }

      toast({
        title: "Issue Reported Successfully",
        description: `Your issue has been submitted and assigned ID #${result.data?.id}`,
      });
      
      navigate("/dashboard");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to submit issue';
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Report an Issue</h1>
        <p className="text-muted-foreground mt-1">
          Help us improve campus facilities by reporting any issues you encounter.
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Issue Details */}
        <div className="rounded-xl border bg-card p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Info className="h-5 w-5 text-primary" />
            Issue Details
          </h2>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Issue Title</Label>
              <Input
                id="title"
                placeholder="Brief description of the issue"
                className="input-focus"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Detailed Description</Label>
              <Textarea
                id="description"
                placeholder="Please provide as much detail as possible about the issue..."
                className="min-h-32 input-focus"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                required
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select value={formData.category} onValueChange={(value) => setFormData({ ...formData, category: value })} required>
                  <SelectTrigger className="input-focus">
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {categories.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        {cat.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority Level</Label>
                <Select value={formData.priority} onValueChange={(value) => setFormData({ ...formData, priority: value })} required>
                  <SelectTrigger className="input-focus">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    {priorityOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        <div className="flex items-center gap-2">
                          <opt.icon className={`h-4 w-4 ${opt.color}`} />
                          {opt.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        </div>

        {/* Location */}
        <div className="rounded-xl border bg-card p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <MapPin className="h-5 w-5 text-primary" />
            Location
          </h2>

          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              placeholder="e.g., Building A, Room 201, Floor 3"
              className="input-focus"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              required
            />
            <p className="text-xs text-muted-foreground">
              Please provide the specific location where the issue is occurring
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="additionalLocation">Additional Location Details</Label>
            <Textarea
              id="additionalLocation"
              placeholder="Near the main entrance, by the water fountain, landmarks, directions, etc."
              className="min-h-20 input-focus"
            />
            <p className="text-xs text-muted-foreground">
              Any additional details that can help locate the issue more precisely
            </p>
          </div>
        </div>

        {/* Image Upload */}
        <div className="rounded-xl border bg-card p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Upload className="h-5 w-5 text-primary" />
            Attachments
          </h2>

          <div
            className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
              dragActive
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(e) =>
                e.target.files && handleFiles(Array.from(e.target.files))
              }
              className="absolute inset-0 cursor-pointer opacity-0"
            />
            <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              <span className="font-medium text-primary">Click to upload</span> or
              drag and drop
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              PNG, JPG or GIF (max 5 images, 10MB each)
            </p>
          </div>

          {images.length > 0 && (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
              {images.map((src, index) => (
                <div key={index} className="group relative aspect-square">
                  <img
                    src={src}
                    alt={`Upload ${index + 1}`}
                    className="h-full w-full rounded-lg object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removeImage(index)}
                    className="absolute -right-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate(-1)}
          >
            Cancel
          </Button>
          <Button type="submit" size="lg">
            <CheckCircle className="mr-2 h-5 w-5" />
            Submit Report
          </Button>
        </div>
      </form>
    </div>
  );
}
