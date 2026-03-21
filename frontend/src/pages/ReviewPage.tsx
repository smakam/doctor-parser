import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { CheckCircle, XCircle, AlertTriangle, ArrowLeft, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { FieldWithConfidence } from "@/components/FieldWithConfidence";
import { ImageGallery } from "@/components/ImageGallery";
import { getExtraction, acceptExtraction, rejectExtraction, correctExtraction } from "@/lib/api";
import type { ExtractionResponse, CorrectRequest } from "@/types/nameboard";
import type { Session } from "@supabase/supabase-js";

interface ReviewPageProps {
  session: Session | null;
}

type Fields = {
  doctor_name: string;
  clinic_name: string;
  specialisation: string;
  qualifications: string;
  medical_registration_no: string;
  address: string;
  pin_code: string;
  consultation_timings: string;
};

function extractValue(field: ExtractionResponse["extracted_data"]["doctor_name"]): string {
  return field?.value ?? "";
}

export default function ReviewPage({ session: _session }: ReviewPageProps) {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const [extraction, setExtraction] = useState<ExtractionResponse | null>(
    location.state?.extraction ?? null
  );
  const [loading, setLoading] = useState(!extraction);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fields, setFields] = useState<Fields>({
    doctor_name: "",
    clinic_name: "",
    specialisation: "",
    qualifications: "",
    medical_registration_no: "",
    address: "",
    pin_code: "",
    consultation_timings: "",
  });

  useEffect(() => {
    if (extraction) {
      const d = extraction.extracted_data;
      setFields({
        doctor_name: extractValue(d.doctor_name),
        clinic_name: extractValue(d.clinic_name),
        specialisation: extractValue(d.specialisation),
        qualifications: extractValue(d.qualifications),
        medical_registration_no: extractValue(d.medical_registration_no),
        address: extractValue(d.address),
        pin_code: extractValue(d.pin_code),
        consultation_timings: extractValue(d.consultation_timings),
      });
    }
  }, [extraction]);

  useEffect(() => {
    if (!extraction && id) {
      getExtraction(id)
        .then(setExtraction)
        .catch(() => setError("Failed to load extraction."))
        .finally(() => setLoading(false));
    }
  }, [id]);

  const handleFieldChange = (key: string, value: string) => {
    setFields((prev) => ({ ...prev, [key]: value }));
  };

  const hasCorrections = (): boolean => {
    if (!extraction) return false;
    const d = extraction.extracted_data;
    return (
      fields.doctor_name !== extractValue(d.doctor_name) ||
      fields.clinic_name !== extractValue(d.clinic_name) ||
      fields.specialisation !== extractValue(d.specialisation) ||
      fields.qualifications !== extractValue(d.qualifications) ||
      fields.medical_registration_no !== extractValue(d.medical_registration_no) ||
      fields.address !== extractValue(d.address) ||
      fields.pin_code !== extractValue(d.pin_code) ||
      fields.consultation_timings !== extractValue(d.consultation_timings)
    );
  };

  const handleAccept = async () => {
    if (!id) return;
    setSubmitting(true);
    setError(null);
    try {
      let result: ExtractionResponse;
      if (hasCorrections()) {
        const corrections: CorrectRequest = {};
        const d = extraction!.extracted_data;
        if (fields.doctor_name !== extractValue(d.doctor_name)) corrections.doctor_name = fields.doctor_name;
        if (fields.clinic_name !== extractValue(d.clinic_name)) corrections.clinic_name = fields.clinic_name;
        if (fields.specialisation !== extractValue(d.specialisation)) corrections.specialisation = fields.specialisation;
        if (fields.qualifications !== extractValue(d.qualifications)) corrections.qualifications = fields.qualifications;
        if (fields.medical_registration_no !== extractValue(d.medical_registration_no)) corrections.medical_registration_no = fields.medical_registration_no;
        if (fields.address !== extractValue(d.address)) corrections.address = fields.address;
        if (fields.pin_code !== extractValue(d.pin_code)) corrections.pin_code = fields.pin_code;
        if (fields.consultation_timings !== extractValue(d.consultation_timings)) corrections.consultation_timings = fields.consultation_timings;
        result = await correctExtraction(id, corrections);
      } else {
        result = await acceptExtraction(id);
      }
      navigate(`/quote/${id}`, { state: { extraction: result, fields } });
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!id) return;
    setSubmitting(true);
    try {
      await rejectExtraction(id);
      navigate("/upload");
    } catch {
      setError("Failed to reject. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!extraction) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <Alert variant="destructive" className="max-w-md">
          <AlertDescription>{error ?? "Extraction not found."}</AlertDescription>
        </Alert>
      </div>
    );
  }

  const overallPct = Math.round(extraction.overall_confidence * 100);
  const confidenceVariant =
    extraction.overall_confidence >= 0.85 ? "success" : extraction.overall_confidence >= 0.70 ? "warning" : "danger";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/upload")}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center">
              <Stethoscope className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-semibold">Review Extraction</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Overall confidence:</span>
          <Badge variant={confidenceVariant}>{overallPct}%</Badge>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Warnings */}
        {extraction.extraction_warnings.length > 0 && (
          <div className="mb-6 space-y-2">
            {extraction.extraction_warnings.map((w, i) => (
              <Alert key={i} variant="warning">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{w}</AlertDescription>
              </Alert>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left — image gallery */}
          <div className="lg:col-span-1">
            <Card className="sticky top-24">
              <CardContent className="pt-6">
                <ImageGallery images={extraction.image_quality} />
              </CardContent>
            </Card>
          </div>

          {/* Right — extracted fields */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">Extracted Information</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Review each field. Highlighted fields need your attention.
                </p>
              </CardHeader>
              <CardContent className="space-y-5">
                <FieldWithConfidence label="Doctor Name" field={extraction.extracted_data.doctor_name} fieldKey="doctor_name" value={fields.doctor_name} onChange={handleFieldChange} />
                <FieldWithConfidence label="Clinic / Hospital Name" field={extraction.extracted_data.clinic_name} fieldKey="clinic_name" value={fields.clinic_name} onChange={handleFieldChange} />
                <FieldWithConfidence label="Specialisation" field={extraction.extracted_data.specialisation} fieldKey="specialisation" value={fields.specialisation} onChange={handleFieldChange} />
                <FieldWithConfidence label="Qualifications" field={extraction.extracted_data.qualifications} fieldKey="qualifications" value={fields.qualifications} onChange={handleFieldChange} />
                <FieldWithConfidence label="Medical Registration No." field={extraction.extracted_data.medical_registration_no} fieldKey="medical_registration_no" value={fields.medical_registration_no} onChange={handleFieldChange} />
                <FieldWithConfidence label="Address" field={extraction.extracted_data.address} fieldKey="address" value={fields.address} onChange={handleFieldChange} multiline />
                <div className="grid grid-cols-2 gap-4">
                  <FieldWithConfidence label="Pin Code" field={extraction.extracted_data.pin_code} fieldKey="pin_code" value={fields.pin_code} onChange={handleFieldChange} />
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">City / State</label>
                    <div className="h-10 px-3 py-2 text-sm border rounded-md bg-muted text-muted-foreground flex items-center">
                      {[extraction.extracted_data.city, extraction.extracted_data.state].filter(Boolean).join(", ") || "—"}
                    </div>
                  </div>
                </div>

                {/* Geocoding result */}
                {(extraction.extracted_data.latitude || extraction.extracted_data.longitude) ? (
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Location Coordinates</label>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="px-3 py-2 text-sm border rounded-md bg-muted text-muted-foreground">
                        <span className="text-xs text-muted-foreground block">Latitude</span>
                        {extraction.extracted_data.latitude?.toFixed(6)}
                      </div>
                      <div className="px-3 py-2 text-sm border rounded-md bg-muted text-muted-foreground">
                        <span className="text-xs text-muted-foreground block">Longitude</span>
                        {extraction.extracted_data.longitude?.toFixed(6)}
                      </div>
                      <div className="px-3 py-2 text-sm border rounded-md bg-muted text-muted-foreground">
                        <span className="text-xs text-muted-foreground block">Method</span>
                        {extraction.geocoding_status.replace("_", " ")}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium">Location Coordinates</label>
                    <div className="px-3 py-2 text-sm border rounded-md bg-muted text-muted-foreground">
                      Not geocoded — {extraction.geocoding_status === "NOT_GEOCODED" ? "Mappls credentials pending or address not found" : extraction.geocoding_status}
                    </div>
                  </div>
                )}
                <FieldWithConfidence label="Consultation Timings" field={extraction.extracted_data.consultation_timings} fieldKey="consultation_timings" value={fields.consultation_timings} onChange={handleFieldChange} />
              </CardContent>
            </Card>

            {/* PII section */}
            {extraction.pii_data && (extraction.pii_data.phones.length > 0 || extraction.pii_data.emails.length > 0) && (
              <Card className="border-amber-200 bg-amber-50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base text-amber-900">Contact Information (Private)</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {extraction.pii_data.phones.map((p, i) => (
                    <p key={i} className="text-sm text-amber-800">Phone: {p}</p>
                  ))}
                  {extraction.pii_data.emails.map((e, i) => (
                    <p key={i} className="text-sm text-amber-800">Email: {e}</p>
                  ))}
                  <p className="text-xs text-amber-700 pt-1">Visible only to you. Not included in the quote unless you add it manually.</p>
                </CardContent>
              </Card>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Action buttons */}
            <div className="flex gap-3">
              <Button onClick={handleAccept} disabled={submitting} className="flex-1" size="lg">
                <CheckCircle className="w-4 h-4 mr-2" />
                {hasCorrections() ? "Save corrections & continue" : "Looks good — continue"}
              </Button>
              <Button onClick={handleReject} disabled={submitting} variant="outline" size="lg">
                <XCircle className="w-4 h-4 mr-2" />
                Reject
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
