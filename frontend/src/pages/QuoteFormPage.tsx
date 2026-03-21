import { useLocation, useNavigate } from "react-router-dom";
import { CheckCircle, Copy, ArrowLeft, Stethoscope } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

interface QuoteField {
  quoteLabel: string;
  quoteFieldName: string;
  value: string;
}

export default function QuoteFormPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const fields = location.state?.fields ?? {};
  const extraction = location.state?.extraction;
  const [copied, setCopied] = useState<string | null>(null);

  const lat = extraction?.extracted_data?.latitude;
  const lng = extraction?.extracted_data?.longitude;
  const city = extraction?.extracted_data?.city;
  const state = extraction?.extracted_data?.state;
  const geocodingStatus = extraction?.geocoding_status;

  const allFieldDefs = [
    { quoteLabel: "Insured Name", quoteFieldName: "insured_name", value: fields.doctor_name ?? "" },
    { quoteLabel: "Occupation / Type of Risk", quoteFieldName: "occupation", value: fields.specialisation ?? "" },
    { quoteLabel: "Qualifications", quoteFieldName: "qualifications", value: fields.qualifications ?? "" },
    { quoteLabel: "Registration Number", quoteFieldName: "registration_number", value: fields.medical_registration_no ?? "" },
    { quoteLabel: "Risk Address", quoteFieldName: "risk_address", value: fields.address ?? "" },
    { quoteLabel: "Risk Pin Code", quoteFieldName: "risk_pin_code", value: fields.pin_code ?? "" },
    { quoteLabel: "City", quoteFieldName: "risk_city", value: city ?? "" },
    { quoteLabel: "State", quoteFieldName: "risk_state", value: state ?? "" },
    { quoteLabel: "Latitude", quoteFieldName: "risk_latitude", value: lat != null ? String(lat) : "" },
    { quoteLabel: "Longitude", quoteFieldName: "risk_longitude", value: lng != null ? String(lng) : "" },
  ];

  const quoteMapping: QuoteField[] = allFieldDefs.filter((f) => f.value);
  const emptyFields: QuoteField[] = allFieldDefs.filter((f) => !f.value);

  const copyToClipboard = (value: string, key: string) => {
    navigator.clipboard.writeText(value);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center gap-3 sticky top-0 z-10">
        <Button variant="ghost" size="icon" onClick={() => navigate("/upload")}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-primary rounded-md flex items-center justify-center">
            <Stethoscope className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold">Quote Form Data</span>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10 space-y-6">
        {/* Success banner */}
        <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
          <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-green-900">Extraction accepted</p>
            <p className="text-xs text-green-700">
              {quoteMapping.length} field{quoteMapping.length !== 1 ? "s" : ""} ready to copy into your quote form
            </p>
          </div>
        </div>

        {/* Geocoding status */}
        {geocodingStatus && geocodingStatus !== "NOT_GEOCODED" ? (
          <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
            <CheckCircle className="w-5 h-5 text-blue-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-blue-900">Location geocoded</p>
              <p className="text-xs text-blue-700">
                Method: {geocodingStatus.replace(/_/g, " ")} · Lat: {lat?.toFixed(6)}, Lng: {lng?.toFixed(6)}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded-lg px-4 py-3">
            <div>
              <p className="text-sm font-medium text-gray-700">Location not geocoded</p>
              <p className="text-xs text-gray-500">Mappls credentials pending approval — lat/long will populate once approved</p>
            </div>
          </div>
        )}

        {/* Populated fields */}
        {quoteMapping.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Extracted Fields — Ready to Use</CardTitle>
              <CardDescription>Click the copy icon to copy any value to clipboard</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {quoteMapping.map((f) => (
                <div key={f.quoteFieldName} className="flex items-start justify-between gap-3 py-2 border-b last:border-0">
                  <div className="space-y-0.5 flex-1 min-w-0">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {f.quoteLabel}
                    </p>
                    <p className="text-sm font-medium text-gray-900 break-words">{f.value}</p>
                    <p className="text-xs text-muted-foreground font-mono">{f.quoteFieldName}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="flex-shrink-0 h-8 w-8"
                    onClick={() => copyToClipboard(f.value, f.quoteFieldName)}
                  >
                    {copied === f.quoteFieldName ? (
                      <CheckCircle className="w-3.5 h-3.5 text-green-600" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Empty fields */}
        {emptyFields.length > 0 && (
          <Card className="border-amber-200">
            <CardHeader>
              <CardTitle className="text-base text-amber-900">Fields to Fill Manually</CardTitle>
              <CardDescription>
                These could not be extracted from the nameboard
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {emptyFields.map((f) => (
                  <Badge key={f.quoteFieldName} variant="warning">{f.quoteLabel}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Button onClick={() => navigate("/upload")} variant="outline" className="w-full">
          Extract another nameboard
        </Button>
      </main>
    </div>
  );
}
