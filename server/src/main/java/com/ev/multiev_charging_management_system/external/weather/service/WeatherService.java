package com.ev.multiev_charging_management_system.external.weather.service;

import com.ev.multiev_charging_management_system.external.ai.dto.PvPredictionRequest;
import com.ev.multiev_charging_management_system.external.weather.AsosApiClient;
import com.ev.multiev_charging_management_system.external.weather.dto.AsosResponse;
import com.ev.multiev_charging_management_system.external.weather.entity.PvActualHourlyData;
import com.ev.multiev_charging_management_system.external.weather.entity.WeatherRawData;
import com.ev.multiev_charging_management_system.external.weather.repository.PvActualHourlyDataRepository;
import com.ev.multiev_charging_management_system.external.weather.repository.WeatherRawDataRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.IntStream;

@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherService {

    private final AsosApiClient asosApiClient;
    private final WeatherRawDataRepository weatherRawDataRepository;
    private final PvActualHourlyDataRepository pvActualHourlyDataRepository;

    private static final DateTimeFormatter ASOS_TIME_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
    public static final String DEFAULT_PV_REGION = "제주도";
    public static final String DEFAULT_PV_ACTUAL_SOURCE = "KPX_REGIONAL_HOURLY_SOLAR_WIND";
    public static final String DEFAULT_PV_FUEL_TYPE = "태양광";
    private static final int PV_DAY_HOURS = 24;
    private static final int PV_ENCODER_CONTEXT_DAYS = 7;
    private static final int PV_ENCODER_CONTEXT_HOURS = PV_DAY_HOURS * PV_ENCODER_CONTEXT_DAYS;

    /**
     * ASOS API에서 특정 날짜의 24시간 기상 데이터를 가져와 DB에 저장한다.
     * 이미 저장된 데이터가 있으면 건너뛴다.
     */
    @Transactional
    public List<WeatherRawData> fetchAndSave(LocalDate date, int asosStationId) {
        LocalDateTime dayStart = date.atStartOfDay();
        LocalDateTime dayEnd = date.atTime(23, 59);

        List<WeatherRawData> existing = weatherRawDataRepository
                .findByAsosStationIdAndObservationTimeBetweenOrderByObservationTimeAsc(
                        asosStationId, dayStart, dayEnd
                );

        if (existing.size() >= 24) {
            log.info("이미 저장된 데이터 있음: date={}, stationId={}, count={}",
                    date, asosStationId, existing.size());
            return existing;
        }

        List<AsosResponse.Item> items = asosApiClient.getHourlyWeather(date, asosStationId);

        List<WeatherRawData> saved = items.stream()
                .map(item -> toEntity(item, asosStationId))
                .filter(entity -> !weatherRawDataRepository.existsByAsosStationIdAndObservationTime(
                        entity.getAsosStationId(), entity.getObservationTime()
                ))
                .map(weatherRawDataRepository::save)
                .toList();

        log.info("기상 데이터 저장 완료: date={}, stationId={}, 신규={}건",
                date, asosStationId, saved.size());
        return getDaily(date, asosStationId);
    }

    /**
     * PV 예측용 encoder context로 사용할 최근 7일(168시간) 기상 데이터를 준비한다.
     * 기준일(baseDate)의 00~23시까지 포함해 baseDate-6일부터 baseDate까지 조회한다.
     */
    @Transactional
    public List<WeatherRawData> fetchAndSaveEncoderWindow(LocalDate baseDate, int asosStationId) {
        return IntStream.rangeClosed(0, PV_ENCODER_CONTEXT_DAYS - 1)
                .mapToObj(dayIndex -> baseDate.minusDays(PV_ENCODER_CONTEXT_DAYS - 1L - dayIndex))
                .map(date -> fetchAndSave(date, asosStationId))
                .flatMap(List::stream)
                .sorted(Comparator.comparing(WeatherRawData::getObservationTime))
                .toList();
    }

    /**
     * DB에서 특정 날짜의 24시간 기상 데이터를 조회한다.
     */
    @Transactional(readOnly = true)
    public List<WeatherRawData> getDaily(LocalDate date, int asosStationId) {
        return weatherRawDataRepository
                .findByAsosStationIdAndObservationTimeBetweenOrderByObservationTimeAsc(
                        asosStationId, date.atStartOfDay(), date.atTime(23, 59)
                );
    }

    /**
     * DB에 이미 저장된 최근 7일(168시간) ASOS 관측 데이터를 조회한다.
     * 외부 ASOS API 호출 없이 현재 RDS 데이터만 사용해야 하는 검증 경로에서 쓴다.
     */
    @Transactional(readOnly = true)
    public List<WeatherRawData> getEncoderWindow(LocalDate baseDate, int asosStationId) {
        return weatherRawDataRepository
                .findByAsosStationIdAndObservationTimeBetweenOrderByObservationTimeAsc(
                        asosStationId,
                        baseDate.minusDays(PV_ENCODER_CONTEXT_DAYS - 1L).atStartOfDay(),
                        baseDate.atTime(23, 59)
                );
    }

    /**
     * DB에 저장된 시간별 기상 데이터를 AI 예측 모듈의 WeatherHourly 형식으로 변환한다.
     *
     * ASOS 필드 → AI 모듈 필드 매핑:
     *   temperature ← ta, rain ← rn, humidity ← hm, snow ← dsnw,
     *   cloud ← dc10Tca, duration ← ss, radiation ← icsr,
     *   day ← LocalDate.getDayOfYear()
     */
    public List<PvPredictionRequest.WeatherHourly> toEncoderWeather(List<WeatherRawData> rawDataList) {
        return rawDataList.stream()
                .sorted(Comparator.comparing(WeatherRawData::getObservationTime))
                .map(data -> PvPredictionRequest.WeatherHourly.builder()
                        .hour(data.getObservationTime().getHour())
                        .temperature(orZero(data.getTemperature()))
                        .rain(orZero(data.getRainfall()))
                        .humidity(orZero(data.getHumidity()))
                        .snow(orZero(data.getSnowfall()))
                        .cloud(orZero(data.getCloudCover()))
                        .duration(orZero(data.getSunshineDuration()))
                        .radiation(orZero(data.getSolarRadiation()))
                        .day(data.getObservationTime().getDayOfYear())
                        .build())
                .toList();
    }

    /**
     * Han Mingu PV 모델이 기대하는 encoder_weather_168h 배열을 만든다.
     * 데이터가 168건보다 많으면 시간순 마지막 168건만 사용하고, 부족하면 그대로 보내되 AI 서버가 24h fallback을 쓴다.
     */
    public List<PvPredictionRequest.WeatherHourly> toEncoderWeather168h(List<WeatherRawData> rawDataList) {
        List<WeatherRawData> sorted = rawDataList.stream()
                .sorted(Comparator.comparing(WeatherRawData::getObservationTime))
                .toList();

        if (sorted.size() > PV_ENCODER_CONTEXT_HOURS) {
            sorted = sorted.subList(sorted.size() - PV_ENCODER_CONTEXT_HOURS, sorted.size());
        }

        return toEncoderWeather(sorted);
    }

    /**
     * 기준일(baseDate)의 실제 PV 발전량을 decoder_pv_24h 형식으로 변환한다.
     * PV 모델은 baseDate 다음 날을 예측하므로, decoder_pv_24h에는 baseDate의 00~23시 실제값을 넣는다.
     */
    @Transactional(readOnly = true)
    public List<PvPredictionRequest.PvHourly> toDecoderPv(LocalDate baseDate, String region) {
        return toDecoderPv(baseDate, region, DEFAULT_PV_ACTUAL_SOURCE, DEFAULT_PV_FUEL_TYPE);
    }

    @Transactional(readOnly = true)
    public List<PvPredictionRequest.PvHourly> toDecoderPv(
            LocalDate baseDate, String region, String source, String fuelType) {
        String resolvedRegion = isBlank(region) ? DEFAULT_PV_REGION : region.trim();
        String resolvedSource = isBlank(source) ? DEFAULT_PV_ACTUAL_SOURCE : source.trim();
        String resolvedFuelType = isBlank(fuelType) ? DEFAULT_PV_FUEL_TYPE : fuelType.trim();

        List<PvActualHourlyData> rows = pvActualHourlyDataRepository
                .findBySourceAndRegionAndFuelTypeAndTradeDateOrderByTradeHourAsc(
                        resolvedSource, resolvedRegion, resolvedFuelType, baseDate
                );
        Map<Integer, Double> pvByHour = new TreeMap<>();
        for (PvActualHourlyData row : rows) {
            if (row.getTradeHour() == null) {
                continue;
            }
            int hour = row.getTradeHour() - 1;
            if (hour >= 0 && hour < PV_DAY_HOURS && row.getGenerationMwh() != null) {
                pvByHour.put(hour, row.getGenerationMwh());
            }
        }

        if (pvByHour.size() < PV_DAY_HOURS) {
            throw new IllegalStateException(
                    "PV 실제 발전량 데이터 부족: baseDate=%s, region=%s, source=%s, fuelType=%s, expected=24, actual=%d"
                            .formatted(baseDate, resolvedRegion, resolvedSource, resolvedFuelType, pvByHour.size())
            );
        }

        return IntStream.range(0, PV_DAY_HOURS)
                .mapToObj(hour -> PvPredictionRequest.PvHourly.builder()
                        .hour(hour)
                        .pvPower(pvByHour.get(hour))
                        .build())
                .toList();
    }

    /**
     * 전체 PV 예측 요청 DTO를 조립한다.
     */
    public PvPredictionRequest buildPvPredictionRequest(
            int chargingStationId, LocalDate baseDate, int asosStationId) {
        return buildPvPredictionRequest(chargingStationId, baseDate, asosStationId, DEFAULT_PV_REGION);
    }

    public PvPredictionRequest buildPvPredictionRequest(
            int chargingStationId, LocalDate baseDate, int asosStationId, String pvRegion) {

        List<WeatherRawData> encoderWindow = fetchAndSaveEncoderWindow(baseDate, asosStationId);
        List<WeatherRawData> dailyRawData = encoderWindow.stream()
                .filter(data -> data.getObservationTime().toLocalDate().isEqual(baseDate))
                .toList();
        List<PvPredictionRequest.WeatherHourly> encoderWeather24h = toEncoderWeather(dailyRawData);
        List<PvPredictionRequest.WeatherHourly> encoderWeather168h = toEncoderWeather168h(encoderWindow);

        log.info("PV 예측 요청 기상 context 조립: stationId={}, baseDate={}, encoder24h={}건, encoder168h={}건",
                chargingStationId, baseDate, encoderWeather24h.size(), encoderWeather168h.size());

        return PvPredictionRequest.builder()
                .requestId("req-pv-" + chargingStationId + "-" + baseDate)
                .timezone("Asia/Seoul")
                .stationId(chargingStationId)
                .baseDate(baseDate.toString())
                .encoderWeather24h(encoderWeather24h)
                .encoderWeather168h(encoderWeather168h)
                .decoderPv24h(toDecoderPv(baseDate, pvRegion))
                .build();
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    private Double orZero(Double value) {
        return value != null ? value : 0.0;
    }

    private WeatherRawData toEntity(AsosResponse.Item item, int asosStationId) {
        return WeatherRawData.builder()
                .asosStationId(asosStationId)
                .observationTime(LocalDateTime.parse(item.getTm(), ASOS_TIME_FMT))
                .stationName(item.getStnNm())
                .temperature(parseDouble(item.getTa()))
                .rainfall(parseDouble(item.getRn()))
                .humidity(parseDouble(item.getHm()))
                .snowfall(parseDouble(item.getDsnw()))
                .cloudCover(parseDouble(item.getDc10Tca()))
                .sunshineDuration(parseDouble(item.getSs()))
                .solarRadiation(parseDouble(item.getIcsr()))
                .windSpeed(parseDouble(item.getWs()))
                .windDirection(parseInt(item.getWd()))
                .build();
    }

    private Double parseDouble(String value) {
        if (value == null || value.isBlank()) return null;
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Integer parseInt(String value) {
        if (value == null || value.isBlank()) return null;
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
