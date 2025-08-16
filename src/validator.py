import sqlite3
import json
import logging
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pyld import jsonld
from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    event_type: Optional[str] = None
    url: Optional[str] = None

class SchemaOrgValidator:
    """Clean schema.org Event validator using PyLD and jsonschema."""
    
    # Schema.org Event schema - much cleaner than hardcoded rules
    EVENT_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "@context": {
                "type": "string",
                "pattern": ".*schema\\.org.*"
            },
            "@type": {
                "type": "string",
                "enum": [
                    "Event", "EducationEvent", "SocialEvent", "BusinessEvent",
                    "ChildrensEvent", "ComedyEvent", "CourseInstance", "DanceEvent",
                    "DeliveryEvent", "ExhibitionEvent", "Festival", "FoodEvent",
                    "LiteraryEvent", "MusicEvent", "PublicationEvent", "SaleEvent",
                    "ScreeningEvent", "SportsEvent", "TheaterEvent", "VisualArtsEvent"
                ]
            },
            "name": {"type": "string", "minLength": 1},
            "startDate": {"type": "string", "format": "date-time"},
            "endDate": {"type": "string", "format": "date-time"},
            "url": {"type": "string", "format": "uri"},
            "description": {"type": "string"},
            "image": {
                "anyOf": [
                    {"type": "string", "format": "uri"},
                    {"type": "array", "items": {"type": "string", "format": "uri"}}
                ]
            },
            "location": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {
                            "@type": {"type": "string"},
                            "name": {"type": ["string", "null"]},
                            "address": {
                                "anyOf": [
                                    {"type": "string"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "@type": {"type": "string"},
                                            "streetAddress": {"type": "string"},
                                            "addressLocality": {"type": "string"},
                                            "addressRegion": {"type": "string"},
                                            "postalCode": {"type": "string"},
                                            "addressCountry": {"type": "string"}
                                        }
                                    }
                                ]
                            },
                            "geo": {
                                "type": "object",
                                "properties": {
                                    "@type": {"type": "string"},
                                    "latitude": {"type": ["number", "string"]},
                                    "longitude": {"type": ["number", "string"]}
                                }
                            },
                            "url": {"type": "string"},
                            "latitude": {"type": ["number", "string"]},
                            "longitude": {"type": ["number", "string"]}
                        },
                        "additionalProperties": True
                    }
                ]
            }
        },
        "required": ["@type", "name", "startDate"],
        "additionalProperties": True
    }
    
    # Local schema.org context to avoid network calls
    SCHEMA_ORG_CONTEXT = {
        "@vocab": "https://schema.org/",
        "name": "https://schema.org/name",
        "startDate": "https://schema.org/startDate",
        "endDate": "https://schema.org/endDate",
        "url": "https://schema.org/url",
        "description": "https://schema.org/description",
        "location": "https://schema.org/location",
        "organizer": "https://schema.org/organizer",
        "image": "https://schema.org/image",
        "offers": "https://schema.org/offers"
    }
    
    def __init__(self):
        self.stats = {'total': 0, 'valid': 0, 'invalid': 0, 'warnings': 0}
    
    def validate_event(self, event_data: Dict[str, Any], url: str = None) -> ValidationResult:
        """Validate event using external libraries."""
        errors = []
        warnings = []
        
        # Step 1: JSON-LD validation using PyLD
        jsonld_errors = self._validate_jsonld(event_data)
        errors.extend(jsonld_errors)
        
        # Step 2: Schema validation using jsonschema
        schema_errors, schema_warnings = self._validate_schema(event_data)
        errors.extend(schema_errors)
        warnings.extend(schema_warnings)
        
        event_type = event_data.get('@type')
        is_valid = len(errors) == 0
        
        # Update stats
        self.stats['total'] += 1
        if is_valid:
            self.stats['valid'] += 1
        else:
            self.stats['invalid'] += 1
        if warnings:
            self.stats['warnings'] += 1
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            event_type=event_type,
            url=url
        )
    
    def _validate_jsonld(self, event_data: Dict[str, Any]) -> List[str]:
        """Validate JSON-LD structure using PyLD."""
        errors = []
        
        try:
            # Use local context to avoid network calls
            local_event = event_data.copy()
            if local_event.get('@context') == 'https://schema.org':
                local_event['@context'] = self.SCHEMA_ORG_CONTEXT
            
            # Validate JSON-LD expansion
            expanded = jsonld.expand(local_event)
            if not expanded or not expanded[0].get('https://schema.org/name'):
                errors.append("Invalid JSON-LD: missing required schema.org properties")
        
        except Exception as e:
            if "loading remote context failed" not in str(e):
                errors.append(f"JSON-LD validation error: {str(e)}")
        
        return errors
    
    def _validate_schema(self, event_data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Validate using jsonschema."""
        errors = []
        warnings = []
        
        try:
            validator = Draft7Validator(self.EVENT_SCHEMA)
            
            for error in validator.iter_errors(event_data):
                if error.validator in ['required', 'type', 'enum']:
                    errors.append(f"Schema error: {error.message}")
                else:
                    warnings.append(f"Schema warning: {error.message}")
        
        except Exception as e:
            errors.append(f"Schema validation failed: {str(e)}")
        
        return errors, warnings

def write_github_step_summary(stats: Dict[str, int], results: List[tuple]) -> None:
    """Write validation results to GitHub Step Summary."""
    github_step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if not github_step_summary:
        return
    
    with open(github_step_summary, 'w') as f:
        f.write("# Event Validation Report\n\n")
        
        # Summary stats
        f.write("## Summary\n\n")
        f.write(f"- **Total Events**: {stats['total']}\n")
        f.write(f"- **Valid Events**: {stats['valid']} ({stats['valid']/stats['total']*100:.1f}%)\n")
        f.write(f"- **Invalid Events**: {stats['invalid']} ({stats['invalid']/stats['total']*100:.1f}%)\n")
        f.write(f"- **Events with Warnings**: {stats['warnings']} ({stats['warnings']/stats['total']*100:.1f}%)\n\n")
        
        # Failed events
        failed_results = [result for _, result in results if not result.is_valid]
        if failed_results:
            f.write("## Failed Events\n\n")
            for result in failed_results:
                f.write(f"### ❌ {result.url or 'Unknown URL'}\n")
                if result.event_type:
                    f.write(f"**Type**: {result.event_type}\n\n")
                if result.errors:
                    f.write("**Errors**:\n")
                    for error in result.errors:
                        f.write(f"- {error}\n")
                    f.write("\n")
        
        # Events with warnings
        warning_results = [result for _, result in results if result.is_valid and result.warnings]
        if warning_results:
            f.write("## Events with Warnings\n\n")
            for result in warning_results:
                f.write(f"### ⚠️ {result.url or 'Unknown URL'}\n")
                if result.event_type:
                    f.write(f"**Type**: {result.event_type}\n\n")
                if result.warnings:
                    f.write("**Warnings**:\n")
                    for warning in result.warnings:
                        f.write(f"- {warning}\n")
                    f.write("\n")

def validate_all_events(output_file: str = None, verbose: bool = False):
    """Validate all events using external libraries."""
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, url, event_json FROM events")
    
    validator = SchemaOrgValidator()
    results = []
    
    logger.info("Starting validation with PyLD + jsonschema...")
    
    for rowid, url, event_json_str in cursor:
        try:
            event = json.loads(event_json_str)
            result = validator.validate_event(event, url)
            results.append((rowid, result))
            
            if verbose and not result.is_valid:
                logger.error(f"❌ {url}: {'; '.join(result.errors)}")
            elif verbose and result.warnings:
                logger.warning(f"⚠️  {url}: {'; '.join(result.warnings)}")
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON error for {url}: {e}")
        except Exception as e:
            logger.error(f"Validation error for {url}: {e}")
    
    conn.close()
    
    # Summary
    stats = validator.stats
    logger.info(f"✅ Validation complete!")
    logger.info(f"📊 Total: {stats['total']}, Valid: {stats['valid']} ({stats['valid']/stats['total']*100:.1f}%), "
                f"Invalid: {stats['invalid']} ({stats['invalid']/stats['total']*100:.1f}%), "
                f"Warnings: {stats['warnings']} ({stats['warnings']/stats['total']*100:.1f}%)")
    
    # Write to GitHub Step Summary
    write_github_step_summary(stats, results)
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump({
                'stats': stats,
                'results': [
                    {
                        'url': result.url,
                        'errors': result.errors,
                        'warnings': result.warnings,
                        'event_type': result.event_type
                    }
                    for rowid, result in results
                    if not result.is_valid or result.warnings  # Only log invalid events or events with warnings
                ]
            }, f, indent=2)
        logger.info(f"📄 Results written to {output_file}")
    
    return results, stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Schema.org Event validator using PyLD + jsonschema")
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    validate_all_events(args.output, args.verbose)
